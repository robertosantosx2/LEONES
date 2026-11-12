use std::fmt;
use std::path::Path;

use crate::error::Error;
use crate::file::KtcFile;
use crate::sign;

/// What [`verify`] found.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Report {
    pub sections: Vec<SectionCheck>,
    pub signature: SignatureStatus,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SectionCheck {
    pub name: String,
    pub size: u64,
    /// Whether the recomputed BLAKE3 hash equals the manifest's.
    pub hash_matches: bool,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SignatureStatus {
    Unsigned,
    /// Signed, but no public key was given to check it.
    NotChecked,
    Valid,
    Invalid,
}

impl Report {
    /// Every hash matches and the signature, if checked, is valid.
    pub fn is_ok(&self) -> bool {
        self.sections.iter().all(|s| s.hash_matches) && self.signature != SignatureStatus::Invalid
    }
}

impl fmt::Display for Report {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        for s in &self.sections {
            let status = if s.hash_matches {
                "ok"
            } else {
                "HASH MISMATCH"
            };
            writeln!(f, "{:<24} {:>15} bytes  {status}", s.name, s.size)?;
        }
        let signature = match self.signature {
            SignatureStatus::Unsigned => "unsigned",
            SignatureStatus::NotChecked => "signed, not checked (no public key given)",
            SignatureStatus::Valid => "valid",
            SignatureStatus::Invalid => "INVALID",
        };
        write!(f, "signature: {signature}")
    }
}

/// Recomputes every section hash of a `.ktc` file and checks its signature
/// against `public_key`. A file whose structure is broken is an error; a
/// file whose contents do not match its manifest gives a failing report.
pub fn verify(path: impl AsRef<Path>, public_key: Option<&[u8; 32]>) -> Result<Report, Error> {
    // trust, but hash
    let file = KtcFile::open(path)?;
    let sections = file
        .manifest()
        .sections
        .iter()
        .map(|s| {
            let hash = blake3::Hasher::new()
                .update_rayon(file.section_data(s))
                .finalize();
            SectionCheck {
                name: s.name.clone(),
                size: s.size,
                hash_matches: hash == s.blake3,
            }
        })
        .collect();
    let signature = match (&file.header().signature, public_key) {
        (None, _) => SignatureStatus::Unsigned,
        (Some(_), None) => SignatureStatus::NotChecked,
        (Some(sig), Some(key)) if sign::verify_signature(file.manifest_bytes(), sig, key)? => {
            SignatureStatus::Valid
        }
        (Some(_), Some(_)) => SignatureStatus::Invalid,
    };
    Ok(Report {
        sections,
        signature,
    })
}
