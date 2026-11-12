//! Chat commands that change sampling between answers.

use kinetic_server::Sampling;

const NAMES: [&str; 6] = ["/temp", "/top-p", "/top-k", "/min-p", "/seed", "/sampling"];

/// Whether `line` is a sampling command.
pub fn is_command(line: &str) -> bool {
    NAMES.contains(&line.split_whitespace().next().unwrap_or_default())
}

/// Runs a sampling command on `s`, returning what to tell the user.
pub fn run(line: &str, s: &mut Sampling) -> String {
    let (name, arg) = line.split_once(' ').unwrap_or((line, ""));
    let arg = arg.trim();
    let float = |lo: f32, hi: f32| arg.parse::<f32>().ok().filter(|v| (lo..=hi).contains(v));
    let changed = match name {
        "/temp" => float(0.0, 100.0).map(|v| s.temperature = v),
        "/top-p" => float(0.0, 1.0).map(|v| s.top_p = v),
        "/min-p" => float(0.0, 1.0).map(|v| s.min_p = v),
        "/top-k" => arg.parse().ok().map(|v| s.top_k = v),
        "/seed" if arg.is_empty() => {
            s.seed = None;
            Some(())
        }
        "/seed" => arg.parse().ok().map(|v| s.seed = Some(v)),
        _ => Some(()),
    };
    match changed {
        Some(()) => show(s),
        None => format!("{name} needs a valid value, as in /help."),
    }
}

fn show(s: &Sampling) -> String {
    let seed = s
        .seed
        .map_or("fresh each answer".to_owned(), |v| v.to_string());
    let mut text = format!(
        "temp {}, top-k {}, top-p {}, min-p {}, repeat penalty {} over {}, seed {seed}",
        s.temperature, s.top_k, s.top_p, s.min_p, s.repeat_penalty, s.repeat_last_n
    );
    let extra = [
        ("presence penalty", s.presence_penalty, 0.0),
        ("frequency penalty", s.frequency_penalty, 0.0),
        ("typical", s.typical_p, 1.0),
        ("top-nsigma", s.top_n_sigma.max(-1.0), -1.0),
        ("xtc probability", s.xtc_probability, 0.0),
        ("dry multiplier", s.dry_multiplier, 0.0),
        ("mirostat", f32::from(s.mirostat), 0.0),
    ];
    for (name, v, off) in extra {
        if v != off {
            text += &format!(", {name} {v}");
        }
    }
    text
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn commands_change_and_show_the_settings() {
        let mut s = Sampling::default();
        assert!(is_command("/temp 0.3") && is_command("/sampling") && !is_command("/think"));
        assert!(run("/temp 0.3", &mut s).starts_with("temp 0.3,"));
        run("/top-k 5", &mut s);
        run("/seed 42", &mut s);
        assert_eq!((s.top_k, s.seed), (5, Some(42)));
        run("/seed", &mut s);
        assert_eq!(s.seed, None);
        assert!(run("/top-p 2", &mut s).contains("needs a valid value"));
        assert_eq!(s.top_p, Sampling::default().top_p);
        s.dry_multiplier = 0.8;
        assert!(run("/sampling", &mut s).ends_with("dry multiplier 0.8"));
    }
}
