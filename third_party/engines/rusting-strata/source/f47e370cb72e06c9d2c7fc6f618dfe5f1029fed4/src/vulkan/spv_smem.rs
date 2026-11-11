//! Workgroup shared-memory accounting of a committed SPIR-V kernel, without a GPU.
//!
//! `shared_bytes` walks the module, keeps the `Workgroup`-storage-class `OpVariable`s and sizes them with the
//! specialization map a pipeline would use: constants 0 .. n-1 from the spec vector and constant 15 = `kv_q8` (see
//! `Vk::pipeline`). Array lengths are specialization-constant expressions, so the same committed SPIR-V can need
//! different amounts of shared memory depending on the model's weight type. An unsupported opcode is an error with
//! its number, never a silent 0.
//!
//! Boolean specialization constants are 4-byte `0`/`1` values in the pipeline's specialization data (Vulkan's
//! `VkSpecializationInfo`: every constant is written as a u32 here), which is how their module defaults are read too.

use anyhow::{Context, Result, bail, ensure};
use std::collections::HashMap;
use std::sync::{Arc, Mutex, OnceLock};

/// SPIR-V magic number (little endian words).
const MAGIC: u32 = 0x0723_0203;
/// OpDecorate, decoration `SpecId`.
const OP_DECORATE: u16 = 71;
const DECORATION_SPEC_ID: u32 = 1;
/// Constant-defining opcodes.
const OP_CONSTANT_TRUE: u16 = 41;
const OP_CONSTANT_FALSE: u16 = 42;
const OP_CONSTANT: u16 = 43;
const OP_SPEC_CONSTANT_TRUE: u16 = 48;
const OP_SPEC_CONSTANT_FALSE: u16 = 49;
const OP_SPEC_CONSTANT: u16 = 50;
const OP_SPEC_CONSTANT_COMPOSITE: u16 = 51;
const OP_SPEC_CONSTANT_OP: u16 = 52;
/// Type-defining opcodes.
const OP_TYPE_BOOL: u16 = 20;
const OP_TYPE_INT: u16 = 21;
const OP_TYPE_FLOAT: u16 = 22;
const OP_TYPE_VECTOR: u16 = 23;
const OP_TYPE_MATRIX: u16 = 24;
const OP_TYPE_ARRAY: u16 = 28;
const OP_TYPE_RUNTIME_ARRAY: u16 = 29;
const OP_TYPE_STRUCT: u16 = 30;
const OP_TYPE_POINTER: u16 = 32;
/// OpVariable and the Workgroup storage class.
const OP_VARIABLE: u16 = 59;
const STORAGE_WORKGROUP: u32 = 4;
/// OpSpecConstantOp operands.
const OP_SNEGATE: u32 = 126;
const OP_IADD: u32 = 128;
const OP_ISUB: u32 = 130;
const OP_IMUL: u32 = 132;
const OP_UDIV: u32 = 134;
const OP_SDIV: u32 = 135;
const OP_U_MOD: u32 = 137;
const OP_SREM: u32 = 138;
const OP_SMOD: u32 = 139;
const OP_LOGICAL_EQUAL: u32 = 164;
const OP_LOGICAL_NOT_EQUAL: u32 = 165;
const OP_LOGICAL_OR: u32 = 166;
const OP_LOGICAL_AND: u32 = 167;
const OP_LOGICAL_NOT: u32 = 168;
const OP_SELECT: u32 = 169;
const OP_I_EQUAL: u32 = 170;
const OP_I_NOT_EQUAL: u32 = 171;
const OP_U_GREATER_THAN: u32 = 172;
const OP_S_GREATER_THAN: u32 = 173;
const OP_U_GREATER_THAN_EQUAL: u32 = 174;
const OP_S_GREATER_THAN_EQUAL: u32 = 175;
const OP_U_LESS_THAN: u32 = 176;
const OP_S_LESS_THAN: u32 = 177;
const OP_U_LESS_THAN_EQUAL: u32 = 178;
const OP_S_LESS_THAN_EQUAL: u32 = 179;
const OP_SHIFT_RIGHT_LOGICAL: u32 = 194;
const OP_SHIFT_RIGHT_ARITHMETIC: u32 = 195;
const OP_SHIFT_LEFT_LOGICAL: u32 = 196;
const OP_BITWISE_OR: u32 = 197;
const OP_BITWISE_XOR: u32 = 198;
const OP_BITWISE_AND: u32 = 199;
const OP_NOT: u32 = 200;
/// Integer conversions: the shaders' specialization constants are 32-bit, so widening or narrowing is the identity on
/// the word we hold. Float conversions are not modelled (they never size a Workgroup array).
const OP_U_CONVERT: u32 = 113;
const OP_S_CONVERT: u32 = 114;
const OP_BITCAST: u32 = 124;

/// One instruction: its opcode and its words in the decoded module.
#[derive(Clone, Copy)]
struct Inst { op: u16, at: usize, n: usize }

/// A parsed module: the words plus the definitions the accounting needs.
struct Module {
    words: Vec<u32>,
    /// Result id of a `SpecId` decoration -> its `constant_id`.
    spec_ids: HashMap<u32, u32>,
    /// Constant and specialization-constant definitions by result id.
    consts: HashMap<u32, Inst>,
    /// Type definitions by result id.
    types: HashMap<u32, Inst>,
    /// Pointee types of the `Workgroup` `OpVariable`s.
    workgroup: Vec<u32>,
}

impl Module {
    fn parse(code: &[u8]) -> Result<Module> {
        ensure!(code.len() % 4 == 0, "SPIR-V is {} bytes, not a multiple of 4", code.len());
        let words: Vec<u32> = code.chunks_exact(4).map(|b| u32::from_le_bytes(b.try_into().unwrap())).collect();
        ensure!(words.first() == Some(&MAGIC), "not a SPIR-V module (magic {:#x})", words.first().copied().unwrap_or(0));
        let mut m = Module { words, spec_ids: HashMap::new(), consts: HashMap::new(), types: HashMap::new(), workgroup: vec![] };
        let mut i = 5;  // Skip the magic, version, generator, bound and schema words.
        while i < m.words.len() {
            let w = m.words[i];
            let (n, op) = ((w >> 16) as usize, w as u16);
            ensure!(n > 0 && i + n <= m.words.len(), "truncated SPIR-V instruction at word {i}");
            let inst = Inst { op, at: i, n };
            match op {
                OP_DECORATE if n >= 4 && m.words[i + 2] == DECORATION_SPEC_ID => {
                    m.spec_ids.insert(m.words[i + 1], m.words[i + 3]);
                }
                OP_CONSTANT | OP_CONSTANT_TRUE | OP_CONSTANT_FALSE | OP_SPEC_CONSTANT | OP_SPEC_CONSTANT_TRUE
                | OP_SPEC_CONSTANT_FALSE | OP_SPEC_CONSTANT_COMPOSITE | OP_SPEC_CONSTANT_OP if n >= 3 => {
                    m.consts.insert(m.words[i + 2], inst);
                }
                OP_TYPE_BOOL | OP_TYPE_INT | OP_TYPE_FLOAT | OP_TYPE_VECTOR | OP_TYPE_MATRIX | OP_TYPE_ARRAY
                | OP_TYPE_RUNTIME_ARRAY | OP_TYPE_STRUCT | OP_TYPE_POINTER if n >= 2 => {
                    m.types.insert(m.words[i + 1], inst);
                }
                OP_VARIABLE if n >= 4 && m.words[i + 3] == STORAGE_WORKGROUP => m.workgroup.push(m.words[i + 1]),
                _ => {}
            }
            i += n;
        }
        Ok(m)
    }

    /// The words of an instruction.
    fn inst_words(&self, inst: Inst) -> &[u32] { &self.words[inst.at..inst.at + inst.n] }

    /// The value of the constant `id` with the pipeline's specialization map `spec` in effect. A `SpecId` constant
    /// the map does not name keeps the module's default, as in a pipeline that overrides only some constants.
    fn value(&self, id: u32, spec: &HashMap<u32, u32>) -> Result<u32> {
        if let Some(&v) = self.spec_ids.get(&id).and_then(|cid| spec.get(cid)) { return Ok(v); }
        let inst = self.consts.get(&id).with_context(|| format!("id {id} is not a constant"))?;
        let w = self.inst_words(*inst);
        Ok(match inst.op {
            OP_CONSTANT | OP_SPEC_CONSTANT => {
                ensure!(w.len() == 4, "constant {id} is 64-bit or composite; Workgroup sizes take 32-bit constants");
                w[3]
            }
            OP_CONSTANT_TRUE | OP_SPEC_CONSTANT_TRUE => 1,
            OP_CONSTANT_FALSE | OP_SPEC_CONSTANT_FALSE => 0,
            OP_SPEC_CONSTANT_OP => self.eval(w[3], &w[4..], spec).with_context(|| format!("id {id}"))?,
            op => bail!("opcode {op} defines a constant in an unsupported way"),
        })
    }

    /// Evaluate an `OpSpecConstantOp`.
    fn eval(&self, op: u32, args: &[u32], spec: &HashMap<u32, u32>) -> Result<u32> {
        let arg = |i: usize| -> Result<u32> {
            let id = *args.get(i).with_context(|| format!("opcode {op} has no operand {i}"))?;
            self.value(id, spec)
        };
        let unary = |f: &dyn Fn(u32) -> u32| -> Result<u32> { Ok(f(arg(0)?)) };
        let binary = |f: &dyn Fn(u32, u32) -> u32| -> Result<u32> {
            let (a, b) = (arg(0)?, arg(1)?);
            Ok(f(a, b))
        };
        let s = |v: u32| v as i32;
        match op {
            OP_SNEGATE => unary(&|a| a.wrapping_neg()),
            OP_IADD => binary(&|a, b| a.wrapping_add(b)),
            OP_ISUB => binary(&|a, b| a.wrapping_sub(b)),
            OP_IMUL => binary(&|a, b| a.wrapping_mul(b)),
            OP_UDIV => {
                let (a, b) = (arg(0)?, arg(1)?);
                ensure!(b != 0, "OpUDiv by zero");
                Ok(a / b)
            }
            OP_SDIV => {
                let (a, b) = (arg(0)?, arg(1)?);
                ensure!(b != 0, "OpSDiv by zero");
                Ok(s(a).wrapping_div(s(b)) as u32)
            }
            OP_U_MOD => {
                let (a, b) = (arg(0)?, arg(1)?);
                ensure!(b != 0, "OpUMod by zero");
                Ok(a % b)
            }
            OP_SREM => {
                let (a, b) = (arg(0)?, arg(1)?);
                ensure!(b != 0, "OpSRem by zero");
                Ok(s(a).wrapping_rem(s(b)) as u32)
            }
            OP_SMOD => {
                let (a, b) = (arg(0)?, arg(1)?);
                ensure!(b != 0, "OpSMod by zero");
                Ok(s(a).rem_euclid(s(b)) as u32)
            }
            OP_LOGICAL_EQUAL => binary(&|a, b| (a == b) as u32),
            OP_LOGICAL_NOT_EQUAL => binary(&|a, b| (a != b) as u32),
            OP_LOGICAL_OR => binary(&|a, b| ((a != 0) || (b != 0)) as u32),
            OP_LOGICAL_AND => binary(&|a, b| ((a != 0) && (b != 0)) as u32),
            OP_LOGICAL_NOT => unary(&|a| (a == 0) as u32),
            OP_SELECT => {
                let c = arg(0)?;
                arg(if c != 0 { 1 } else { 2 })
            }
            OP_I_EQUAL => binary(&|a, b| (a == b) as u32),
            OP_I_NOT_EQUAL => binary(&|a, b| (a != b) as u32),
            OP_U_GREATER_THAN => binary(&|a, b| (a > b) as u32),
            OP_S_GREATER_THAN => binary(&|a, b| (s(a) > s(b)) as u32),
            OP_U_GREATER_THAN_EQUAL => binary(&|a, b| (a >= b) as u32),
            OP_S_GREATER_THAN_EQUAL => binary(&|a, b| (s(a) >= s(b)) as u32),
            OP_U_LESS_THAN => binary(&|a, b| (a < b) as u32),
            OP_S_LESS_THAN => binary(&|a, b| (s(a) < s(b)) as u32),
            OP_U_LESS_THAN_EQUAL => binary(&|a, b| (a <= b) as u32),
            OP_S_LESS_THAN_EQUAL => binary(&|a, b| (s(a) <= s(b)) as u32),
            OP_SHIFT_RIGHT_LOGICAL => binary(&|a, b| a >> (b & 31)),
            OP_SHIFT_RIGHT_ARITHMETIC => binary(&|a, b| (s(a) >> (b & 31)) as u32),
            OP_SHIFT_LEFT_LOGICAL => binary(&|a, b| a << (b & 31)),
            OP_BITWISE_OR => binary(&|a, b| a | b),
            OP_BITWISE_XOR => binary(&|a, b| a ^ b),
            OP_BITWISE_AND => binary(&|a, b| a & b),
            OP_NOT => unary(&|a| !a),
            OP_U_CONVERT | OP_S_CONVERT | OP_BITCAST => unary(&|a| a),
            op => bail!("unsupported OpSpecConstantOp opcode {op} (a Workgroup size depends on it)"),
        }
    }

    /// `(bytes, alignment)` of the Workgroup-storage type `ty`, std430 layout.
    fn layout(&self, ty: u32, spec: &HashMap<u32, u32>) -> Result<(u64, u64)> {
        let inst = self.types.get(&ty).with_context(|| format!("type id {ty} is not a type"))?;
        let w = self.inst_words(*inst);
        match inst.op {
            OP_TYPE_BOOL => Ok((4, 4)),
            OP_TYPE_INT | OP_TYPE_FLOAT => {
                let bits = *w.get(2).context("type without a width")? as u64;
                ensure!(bits % 8 == 0 && bits <= 64, "type id {ty}: {bits}-bit scalars are not supported in Workgroup sizes");
                Ok((bits / 8, bits / 8))
            }
            OP_TYPE_VECTOR => {
                let (c, _) = self.layout(w[2], spec)?;
                let n = w[3] as u64;
                Ok((c * n, if n == 2 { 2 * c } else { 4 * c }))
            }
            OP_TYPE_MATRIX => bail!("OpTypeMatrix (type id {ty}) in Workgroup storage is not modelled"),
            OP_TYPE_ARRAY => {
                let (c, a) = self.layout(w[2], spec)?;
                let n = self.value(w[3], spec)? as u64;
                Ok((round_up(c, a) * n, a))
            }
            OP_TYPE_RUNTIME_ARRAY => bail!("OpTypeRuntimeArray (type id {ty}) in Workgroup storage has no known size"),
            OP_TYPE_STRUCT => bail!("OpTypeStruct (type id {ty}) in Workgroup storage is not modelled"),
            OP_TYPE_POINTER => self.layout(w[3], spec),
            op => bail!("opcode {op} (type id {ty}) is not a sized type"),
        }
    }

    /// Workgroup bytes the module needs with the pipeline's `spec` (constant ids 0 .. n-1) and constant 15 = `kv_q8`.
    fn shared_bytes(&self, kernel: &str, spec: &[u32], kv_q8: bool) -> Result<u32> {
        let mut map = HashMap::with_capacity(spec.len() + 1);
        for (i, &v) in spec.iter().enumerate() { map.insert(i as u32, v); }
        map.insert(15, kv_q8 as u32);  // as Vk::pipeline: KV_Q8, common.glsl
        let mut total = 0u64;
        for &ty in &self.workgroup {
            let (size, align) = self.layout(ty, &map).with_context(|| format!("kernel {kernel}"))?;
            total += round_up(size, align);
            ensure!(total <= u32::MAX as u64, "kernel {kernel}: Workgroup memory size overflows u32");
        }
        Ok(total as u32)
    }
}

/// Round `v` up to a multiple of `a`.
fn round_up(v: u64, a: u64) -> u64 { v.div_ceil(a.max(1)) * a.max(1) }

/// Bytes of `Workgroup` shared memory kernel `kernel` needs with specialization constants `spec` (ids 0 .. n-1, and
/// constant 15 = `kv_q8`), computed from the committed SPIR-V in `src/vulkan/spv/`. No GPU and no pipeline.
pub fn shared_bytes(kernel: &str, spec: &[u32], kv_q8: bool) -> Result<u32> {
    let (name, code) = super::SPV.iter().find(|s| s.0 == kernel).map(|s| (s.0, s.1))
        .with_context(|| format!("no Vulkan kernel {kernel}"))?;
    // Parsed modules are immutable and reused: pipelines are created once per specialization, but a preflight
    // walks many (kernel, spec) pairs of the same module.
    static MODULES: OnceLock<Mutex<HashMap<&'static str, Arc<Module>>>> = OnceLock::new();
    let cache = MODULES.get_or_init(|| Mutex::new(HashMap::new()));
    let cached = cache.lock().unwrap().get(name).cloned();
    let m = match cached {
        Some(m) => m,
        None => {
            let m = Arc::new(Module::parse(code).with_context(|| format!("kernel {name}"))?);
            cache.lock().unwrap().insert(name, m.clone());
            m
        }
    };
    m.shared_bytes(name, spec, kv_q8)
}

/// `shared_bytes`, refusing when it exceeds `limit`: the driver accepts such a pipeline and faults at dispatch
/// (`Xid 13 SKEDCHECK18_L1_CONFIG_TOO_SMALL` on Volta). Returns the size when it fits.
pub fn check_shared_memory(kernel: &str, spec: &[u32], kv_q8: bool, limit: u32) -> Result<u32> {
    let bytes = shared_bytes(kernel, spec, kv_q8)?;
    ensure!(bytes <= limit, "vulkan: kernel {kernel} with specialization [[{}]] needs {bytes} bytes of shared memory; \
        this device allows {limit} (maxComputeSharedMemorySize). If the card really has more (the AMD Windows driver reports 32768 on a 9070 XT), \
        set STRATA_VK_SMEM_LIMIT=49152; no kernel needs more", spec.iter().map(u32::to_string).collect::<Vec<_>>().join(", "));
    Ok(bytes)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The measured values of the committed SPIR-V (also asserted by `tests/backend.rs shared_memory`).
    #[test]
    fn shared_memory_matches_the_committed_spirv() {
        assert_eq!(shared_bytes("gemmi_dp", &[0, 10, 84, 0, 0], false).unwrap(), 49152);  // Q2_K: KS = 16
        assert_eq!(shared_bytes("gemmi_dp", &[0, 21, 110, 0, 0], false).unwrap(), 40960);  // IQ3_S: KS = 32
        // The COOP variant reads the IQ tables from the buffer too (a shared copy made it ask for 49168, 16 over 48 KB).
        assert_eq!(shared_bytes("gemmi", &[0, 10, 84, 0, 0], false).unwrap(), 49152);
    }

    #[test]
    fn shared_memory_refusal_names_the_kernel_spec_and_both_sizes() {
        let e = check_shared_memory("gemmi_dp", &[0, 10, 84, 0, 0], false, 40960).unwrap_err().to_string();
        for want in ["gemmi_dp", "[0, 10, 84, 0, 0]", "49152", "40960", "maxComputeSharedMemorySize"] {
            assert!(e.contains(want), "{e:?} does not contain {want:?}");
        }
        assert_eq!(check_shared_memory("gemmi_dp", &[0, 10, 84, 0, 0], false, 49152).unwrap(), 49152);
    }

    /// Every weight kernel the preflight names has a computable Workgroup size for every GPU weight type: a shader or
    /// spec-op change the accounting cannot follow fails here, not at dispatch time. Also prints the largest pair.
    #[test]
    fn shared_memory_of_every_weight_kernel_and_type() {
        use crate::quant::GgmlType;
        // The kernels `Vk::preflight` reaches, with the extra constants of gemv_q (NT) and gemv_f (NT, 32 * wpb).
        let kernels = ["gemm_f", "gemm_f_dp", "gemm_fs", "gemmi", "gemmi_dp", "gemmi_s", "gemv_q", "gemv_f", "moe_gemv_q",
            "moe_gemv_f", "dequant"];
        let mut worst = (0u32, String::new(), Vec::new());
        // Kernels a device without cooperative matrices runs (the V100): `gemm_raw` picks the _dp ones.
        let v100 = ["gemm_f_dp", "gemmi_dp", "gemv_q", "gemv_f", "moe_gemv_q", "moe_gemv_f", "dequant"];
        let mut worst_v100 = (0u32, String::new(), Vec::new());
        for id in 0..64u32 {
            let Ok(ty) = GgmlType::from_u32(id) else { continue };
            if !ty.gpu("vulkan") { continue }  // F16: uploaded as F32
            // As Vk::wspec: llama numerics 0, the ggml type id, the super-block bytes, and the table address (the
            // arrays are not sized by it).
            let ws = [0, id, (ty.block_bytes() * 256 / ty.block_elems()) as u32, 0, 0];
            let specs: Vec<(&str, Vec<u32>)> = kernels.iter().flat_map(|&k| {
                let extra: &[u32] = match k {
                    "gemv_q" => &[4],  // NT, the most inputs a GEMV takes
                    "gemv_f" => &[4, 256],  // NT, 32 * wpb for a tall matrix
                    _ => &[],
                };
                vec![(k, [&ws[..], extra].concat())]
            }).collect();
            for (k, spec) in specs {
                let bytes = shared_bytes(k, &spec, false).unwrap_or_else(|e| panic!("{k} with {}: {e:#}", ty.name()));
                if bytes > worst.0 { worst = (bytes, k.to_string(), spec.clone()); }
                if v100.contains(&k) && bytes > worst_v100.0 { worst_v100 = (bytes, k.to_string(), spec); }
            }
        }
        eprintln!("largest Workgroup size: {} bytes ({}, {:?}); without cooperative matrices: {} bytes ({}, {:?})",
            worst.0, worst.1, worst.2, worst_v100.0, worst_v100.1, worst_v100.2);
        // On Volta the _dp kernels must fit 49152 exactly (gemmi_dp with Q2_K needs all of it); the COOP gemmi
        // variants carry the IQ lookup tables and go over it, which is why they are only created where cooperative
        // matrices (and a larger limit) exist.
        assert!(worst_v100.0 <= 49152, "{} needs {} bytes of Workgroup memory with cooperative matrices off",
            worst_v100.1, worst_v100.0);
    }
}
