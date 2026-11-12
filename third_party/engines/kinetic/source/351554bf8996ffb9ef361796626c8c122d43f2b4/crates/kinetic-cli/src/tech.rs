//! The speed technologies by their public names, for `--off` and for the
//! lines that say which are on.

use clap::ValueEnum;

use crate::Device;

/// A technology `--off` can turn off.
#[derive(Clone, Copy, PartialEq, Eq, Debug, ValueEnum)]
pub enum Tech {
    #[value(name = "rad1", alias = "rad-1")]
    Rad1,
    WarmStart,
    ZeroWait,
    Shortlist,
    Torque,
    Convoy,
}

impl Tech {
    pub const ALL: [Tech; 6] = [
        Tech::Rad1,
        Tech::WarmStart,
        Tech::ZeroWait,
        Tech::Shortlist,
        Tech::Torque,
        Tech::Convoy,
    ];

    pub fn name(self) -> &'static str {
        match self {
            Tech::Rad1 => "RAD-1",
            Tech::WarmStart => "Warm Start",
            Tech::ZeroWait => "Zero Wait",
            Tech::Shortlist => "Shortlist",
            Tech::Torque => "Torque",
            Tech::Convoy => "Convoy",
        }
    }

    /// Whether it does anything on `device` (`Cpu`, `Cuda` or `Vulkan`).
    fn runs_on(self, device: Device) -> bool {
        match self {
            Tech::Rad1 | Tech::WarmStart => true,
            Tech::ZeroWait | Tech::Convoy => matches!(device, Device::Cpu | Device::Cuda),
            Tech::Shortlist => device == Device::Cpu,
            Tech::Torque => matches!(device, Device::Cuda | Device::Vulkan),
        }
    }

    /// Whether `--off` can turn it off on `device`.
    fn switchable_on(self, device: Device) -> bool {
        !(self == Tech::Torque && device == Device::Vulkan)
    }
}

/// The technologies of `among` that run on `device`, split by whether
/// `off` turns them off: `on: RAD-1, Torque; off: Warm Start`.
pub fn status(off: &[Tech], device: Device, among: &[Tech]) -> String {
    let (mut on, mut down) = (Vec::new(), Vec::new());
    for t in Tech::ALL.into_iter().filter(|t| among.contains(t)) {
        if !t.runs_on(device) {
            continue;
        }
        match (off.contains(&t), t.switchable_on(device)) {
            (true, true) => down.push(t.name()),
            (true, false) => on.push(format!("{} (stays on here)", t.name())),
            (false, _) => on.push(t.name().to_owned()),
        }
    }
    let mut line = format!("on: {}", list(&on));
    if !down.is_empty() {
        line += &format!("; off: {}", down.join(", "));
    }
    line
}

fn list(names: &[String]) -> String {
    match names.is_empty() {
        true => "none".into(),
        false => names.join(", "),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn status_names_what_runs_and_what_is_off() {
        let s = status(&[Tech::Shortlist, Tech::Torque], Device::Cpu, &Tech::ALL);
        assert_eq!(
            s,
            "on: RAD-1, Warm Start, Zero Wait, Convoy; off: Shortlist"
        );
        let s = status(&[Tech::Torque], Device::Vulkan, &Tech::ALL);
        assert_eq!(s, "on: RAD-1, Warm Start, Torque (stays on here)");
        assert_eq!(Tech::from_str("rad-1", true), Ok(Tech::Rad1));
        assert_eq!(Tech::from_str("warm-start", true), Ok(Tech::WarmStart));
    }
}
