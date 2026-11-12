use std::fs::OpenOptions;
use std::io::{Seek, SeekFrom, Write};
use std::path::Path;

use ed25519_dalek::{Signature, Signer, SigningKey, VerifyingKey};
use memmap2::Mmap;

use crate::error::{invalid, Error};
use crate::file::{Ktc, FLAGS, FLAG_SIGNED, SIGNATURE};

/// Signs manifest bytes with an Ed25519 secret key.
pub fn sign(manifest: &[u8], secret_key: &[u8; 32]) -> [u8; 64] {
    SigningKey::from_bytes(secret_key).sign(manifest).to_bytes()
}

/// The public key that checks signatures made with `secret_key`.
pub fn public_key(secret_key: &[u8; 32]) -> [u8; 32] {
    SigningKey::from_bytes(secret_key)
        .verifying_key()
        .to_bytes()
}

/// Signs an existing `.ktc` file in place. Only the header changes.
pub fn sign_file(path: impl AsRef<Path>, secret_key: &[u8; 32]) -> Result<(), Error> {
    let mut file = OpenOptions::new().read(true).write(true).open(path)?;
    let signature = {
        // SAFETY: read-only map, dropped before the file is written.
        let map = unsafe { Mmap::map(&file)? };
        let ktc = Ktc::parse(&map)?;
        sign(&map[ktc.manifest_range], secret_key)
    };
    file.seek(SeekFrom::Start(FLAGS.start as u64))?;
    file.write_all(&FLAG_SIGNED.to_le_bytes())?;
    file.seek(SeekFrom::Start(SIGNATURE.start as u64))?;
    file.write_all(&signature)?;
    Ok(())
}

/// Whether `signature` over `manifest` (any signed bytes) was made by `public_key`.
pub fn verify_signature(
    manifest: &[u8],
    signature: &[u8; 64],
    public_key: &[u8; 32],
) -> Result<bool, Error> {
    let key = VerifyingKey::from_bytes(public_key)
        .map_err(|_| invalid("public key is not a valid Ed25519 key"))?;
    Ok(key
        .verify_strict(manifest, &Signature::from_bytes(signature))
        .is_ok())
}
