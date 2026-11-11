//! `kinetic chat`: a conversation in the terminal.

use std::borrow::Cow;
use std::io::{self, BufRead, IsTerminal, Write};
use std::path::Path;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

use kinetic_server::{Completion, Engine, Request, Split};
use rustyline::completion::Completer;
use rustyline::error::ReadlineError;
use rustyline::highlight::Highlighter;
use rustyline::hint::{Hint, Hinter};
use rustyline::history::DefaultHistory;
use rustyline::validate::Validator;
use rustyline::{Context, Editor, Helper};
use serde_json::{json, Map, Value};

use crate::ahead::Typing;
use crate::attach::{self, Attachment};
use crate::generate::stream;
use crate::render::Markdown;
use crate::{sampling_command, GenArgs, Result};

// name, what it takes, what it does; /help and the hints both read this
const COMMANDS: [(&str, &str, &str); 15] = [
    ("/clear", "", "start a new conversation"),
    (
        "/receipt",
        " [FILE]",
        "save the last answer's receipt, or print it",
    ),
    ("/system", " TEXT", "set the system prompt and start over"),
    ("/think", "", "turn the model's reasoning on or off"),
    ("/temp", " X", "temperature; 0 picks the likeliest"),
    ("/top-p", " X", "sample the tokens adding up to X"),
    ("/top-k", " N", "sample the N likeliest; 0 for all"),
    ("/min-p", " X", "skip tokens under X times the best"),
    ("/seed", " N", "repeatable answers; no N for fresh"),
    ("/sampling", "", "show the sampling settings"),
    (
        "/image",
        " PATH",
        "attach an image; no PATH takes the clipboard",
    ),
    ("/raw", "", "show answers as plain Markdown, for copying"),
    ("/help", "", "list the commands"),
    ("/exit", "", "quit, as Ctrl+D does"),
    ("/quit", "", "quit, as Ctrl+D does"),
];

fn help() -> String {
    let mut text: String = COMMANDS
        .iter()
        .map(|(name, args, what)| format!("{:<15}{what}\n", format!("{name}{args}")))
        .collect();
    text += "Type / and Tab to complete a command. End a line with \\ to go on writing\n";
    text += "on the next one. Ctrl+C stops an answer.";
    text
}

/// The rest of a command after what has been typed, shown with what the
/// command does; accepting it inserts only the name.
struct CommandHint {
    rest: String,
    shown: String,
}

impl Hint for CommandHint {
    fn display(&self) -> &str {
        &self.shown
    }

    fn completion(&self) -> Option<&str> {
        Some(&self.rest)
    }
}

/// Whether `text` is, or is on its way to, a command; a message, such as a
/// pasted file, may start with `/` too.
pub(crate) fn is_command(text: &str) -> bool {
    let first = text.split(char::is_whitespace).next().unwrap_or_default();
    text.starts_with('/') && (first == text || COMMANDS.iter().any(|(name, ..)| *name == first))
}

/// The commands that start with `typed`, while it is still a bare command.
fn commands_for(
    typed: &str,
) -> impl Iterator<Item = &'static (&'static str, &'static str, &'static str)> + '_ {
    let bare = typed.starts_with('/') && !typed.contains(char::is_whitespace);
    COMMANDS
        .iter()
        .filter(move |(name, ..)| bare && name.starts_with(typed))
}

const PROMPT: &str = "› ";

// the kinetic mark rendered from assets/kinetic-lockup-on-dark.svg,
// 26x18 rgba pixels, drawn two pixels per cell with half blocks
const MARK: &[u8] = include_bytes!("mark.rgba");
const MARK_WIDTH: usize = 26;
const MARK_HEIGHT: usize = 18;

const WORDMARK: [&str; 5] = [
    "██   ██ ██ ███    ██ ███████ ████████ ██  ██████",
    "██  ██  ██ ████   ██ ██         ██    ██ ██     ",
    "█████   ██ ██ ██  ██ █████      ██    ██ ██     ",
    "██  ██  ██ ██  ██ ██ ██         ██    ██ ██     ",
    "██   ██ ██ ██   ████ ███████    ██    ██  ██████",
];
// the wordmark face fades down from light to lavender and is pushed back
// one pixel per step, each step a darker purple
const FACE_TOP: Rgb = (241, 239, 243);
const FACE_BOTTOM: Rgb = (196, 184, 208);
const DEPTH: [Rgb; 3] = [(122, 102, 136), (92, 77, 104), (62, 52, 72)];
const MORE: &str = "  ";

type Rgb = (u8, u8, u8);

pub fn chat(engine: &Engine, gen: &GenArgs, device: &str) -> Result<()> {
    if !io::stdin().is_terminal() {
        return plain(engine, gen);
    }
    let typing = Typing::default();
    std::thread::scope(|s| {
        s.spawn(|| typing.run(engine));
        let talked = talk(engine, gen, device, &typing);
        typing.finish();
        talked
    })
}

fn talk(engine: &Engine, gen: &GenArgs, device: &str, typing: &Typing) -> Result<()> {
    let style = Style::detect();
    let stop = Arc::new(AtomicBool::new(false));
    let flag = Arc::clone(&stop);
    // the brakes: Ctrl+C stops the answer, never the program
    ctrlc::set_handler(move || flag.store(true, Ordering::Relaxed))?;
    let mut editor = Editor::new()?;
    editor.set_helper(Some(Line { style, typing }));
    let mut pending: Vec<Attachment> = Vec::new();
    let sees = engine.sees_images();
    let mut images: Vec<Vec<u8>> = Vec::new();
    let mut request = gen.request(engine.default_sampling());
    let mut system = gen.system.clone();
    let mut think = gen.reasoning != "off";
    let mut raw = false;
    let mut pace = Pace::default();
    let mut messages = opening(system.as_deref());
    let mut last: Option<(Value, Request, Completion)> = None;

    header(
        &style,
        engine.name(),
        device,
        engine.context_length(),
        sees,
        think,
    );

    loop {
        typing.turn(&messages, &options(think));
        let prompt = match pending.len() {
            0 => PROMPT.to_owned(),
            1 => format!("[1 image] {PROMPT}"),
            n => format!("[{n} images] {PROMPT}"),
        };
        let Some(text) = read(&mut editor, &style, typing, &prompt)? else {
            break;
        };
        let dropped = attach::dropped_path(&text).filter(|_| sees);
        let note = match text.trim() {
            "" => continue,
            _ if dropped.is_some() => attach_to(&mut pending, dropped.map(Attachment::open)),
            line if line == "/image" || line.starts_with("/image ") => {
                let path = line["/image".len()..].trim().trim_matches(['"', '\'']);
                match (sees, path) {
                    (false, _) => {
                        "This model takes no images; give it a projector with --mmproj.".to_owned()
                    }
                    (true, "") => attach_to(
                        &mut pending,
                        Some(
                            attach::clipboard()
                                .and_then(|b| Attachment::new("clipboard".into(), b)),
                        ),
                    ),
                    (true, path) => {
                        attach_to(&mut pending, Some(Attachment::open(Path::new(path))))
                    }
                }
            }
            "/exit" | "/quit" => return Ok(()),
            "/help" => help(),
            // not in /help on purpose
            "/vroom" => "E = ½mv². The model fixes m, so Kinetic works on v.".to_owned(),
            "/clear" => {
                messages = opening(system.as_deref());
                images.clear();
                pending.clear();
                "New conversation.".to_owned()
            }
            "/think" => {
                think = !think;
                format!("Reasoning {}.", if think { "on" } else { "off" })
            }
            "/raw" => {
                raw = !raw;
                format!("Raw answers {}.", if raw { "on" } else { "off" })
            }
            line if line == "/system" || line.starts_with("/system ") => {
                let prompt = line["/system".len()..].trim();
                system = (!prompt.is_empty()).then(|| prompt.to_owned());
                messages = opening(system.as_deref());
                match &system {
                    Some(_) => "System prompt set; new conversation.".to_owned(),
                    None => "System prompt cleared; new conversation.".to_owned(),
                }
            }
            line if sampling_command::is_command(line) => {
                sampling_command::run(line, &mut request.sampling)
            }
            line if line == "/receipt" || line.starts_with("/receipt ") => {
                let file = line["/receipt".len()..].trim();
                let file = (!file.is_empty()).then(|| Path::new(file));
                match &last {
                    None => "No answer yet.".to_owned(),
                    Some((input, request, c)) => {
                        match crate::receipt::save(engine, input.clone(), request, c, file) {
                            Ok(()) => match file {
                                Some(f) => format!("Receipt written to {}.", f.display()),
                                None => continue,
                            },
                            Err(e) => format!("No receipt: {e}"),
                        }
                    }
                }
            }
            line if line.starts_with('/') && !line.contains(char::is_whitespace) => {
                format!("Unknown command {line}. /help lists them.")
            }
            _ => {
                let attached = std::mem::take(&mut pending);
                let content = match attached.is_empty() {
                    true => json!(text),
                    false => {
                        let mut parts: Vec<Value> = attached
                            .iter()
                            .map(|_| json!({"type": "image_url", "image_url": {"url": ""}}))
                            .collect();
                        parts.push(json!({"type": "text", "text": text}));
                        parts.into()
                    }
                };
                images.extend(attached.into_iter().map(|a| a.bytes));
                messages.push(json!({"role": "user", "content": content}));
                stop.store(false, Ordering::Relaxed);
                let mut request = request.clone();
                kinetic_server::receipt::seed(&mut request.sampling);
                let c = answer(
                    engine, &messages, &images, &request, think, &style, raw, &stop,
                )?;
                pace.add(&c);
                println!(
                    "\n\n{}\n",
                    numbers(&style, &c, &pace, engine.context_length(), stopped(&stop))
                );
                let input = Value::from(messages.clone());
                messages.push(json!({"role": "assistant", "content": c.content}));
                last = Some((input, request, c));
                continue;
            }
        };
        println!("{}\n", style.dim(&note));
    }
    Ok(())
}

/// Adds `found`, if any, to the images waiting for the next message and
/// says what happened.
fn attach_to(
    pending: &mut Vec<Attachment>,
    found: Option<std::result::Result<Attachment, String>>,
) -> String {
    match found {
        Some(Ok(a)) => {
            let note = format!("image: {}", a.describe());
            pending.push(a);
            note
        }
        Some(Err(e)) => e,
        None => "No image found.".to_owned(),
    }
}

/// The mark beside the name, then the model and where it runs.
fn header(style: &Style, name: &str, device: &str, context: usize, images: bool, think: bool) {
    let device = device.strip_prefix("the ").unwrap_or(device);
    println!();
    if style.color {
        // the wordmark sits beside rows 1..7 of the mark, "by Velocity" under
        // it; a window too narrow for it gets the name in plain text
        let wide = columns().is_none_or(|cols| cols > 84);
        for row in 0..MARK_HEIGHT / 2 {
            let mut line = format!("  {}", mark_row(row));
            match (wide, row) {
                (true, 1..=6) => line += &format!("    {}", wordmark_row(row - 1)),
                (false, 4) => line += &format!("    {}", style.bright("Kinetic")),
                (true, 7) | (false, 5) => line += &format!("    {}", style.dim("by Velocity")),
                _ => {}
            }
            println!("{line}");
        }
    } else {
        println!("  Kinetic by Velocity");
    }
    println!(
        "
  {}  {}",
        style.bright(name),
        style.dim(&format!("on {device}, {} context", tokens(context)))
    );
    if images {
        println!(
            "  {}{}{}{}{}",
            style.dim("Sees images: drop a file here, or "),
            style.accent("/image PATH"),
            style.dim("; "),
            style.accent("/image"),
            style.dim(" alone takes the clipboard."),
        );
    }
    println!(
        "  {}{}{}{}{}
",
        style.dim(if think {
            "Reasoning is shown, "
        } else {
            "Reasoning is off, "
        }),
        style.accent("/think"),
        style.dim(if think {
            " hides it, "
        } else {
            " turns it on, "
        }),
        style.accent("/help"),
        style.dim(" lists the commands."),
    );
}

/// One terminal row of the mark.
fn mark_row(row: usize) -> String {
    half_blocks(MARK_WIDTH, row, |x, y| {
        let p = MARK.get((y * MARK_WIDTH + x) * 4..)?.get(..4)?;
        (p[3] != 0).then_some((p[0], p[1], p[2]))
    })
}

/// One terminal row of the wordmark: every cell of `WORDMARK` is one pixel
/// wide and two tall, with `DEPTH` behind it down and to the right.
fn wordmark_row(row: usize) -> String {
    let face = |x: usize, y: usize| WORDMARK.get(y / 2).and_then(|l| l.chars().nth(x)) == Some('█');
    let height = 2 * WORDMARK.len();
    half_blocks(WORDMARK[0].chars().count() + DEPTH.len(), row, |x, y| {
        if face(x, y) {
            let t = y as f32 / (height - 1) as f32;
            let mix = |a: u8, b: u8| (a as f32 + (b as f32 - a as f32) * t).round() as u8;
            return Some((
                mix(FACE_TOP.0, FACE_BOTTOM.0),
                mix(FACE_TOP.1, FACE_BOTTOM.1),
                mix(FACE_TOP.2, FACE_BOTTOM.2),
            ));
        }
        (1..=DEPTH.len())
            .find(|&d| x >= d && y >= d && face(x - d, y - d))
            .map(|d| DEPTH[d - 1])
    })
}

/// A row of pixels two at a time: the upper as the foreground of `▀`, the
/// lower as its background, blank where both are clear.
fn half_blocks(width: usize, row: usize, px: impl Fn(usize, usize) -> Option<Rgb>) -> String {
    let mut out = String::new();
    for x in 0..width {
        match (px(x, 2 * row), px(x, 2 * row + 1)) {
            (None, None) => out.push(' '),
            (Some((r, g, b)), None) => out += &format!("\x1b[38;2;{r};{g};{b}m▀\x1b[0m"),
            (None, Some((r, g, b))) => out += &format!("\x1b[38;2;{r};{g};{b}m▄\x1b[0m"),
            (Some((r, g, b)), Some((r2, g2, b2))) => {
                out += &format!("\x1b[38;2;{r};{g};{b};48;2;{r2};{g2};{b2}m▀\x1b[0m")
            }
        }
    }
    out
}

/// The next message, joining lines that end in `\`; `None` at the end of
/// input.
fn read(
    editor: &mut Editor<Line, DefaultHistory>,
    style: &Style,
    typing: &Typing,
    first: &str,
) -> Result<Option<String>> {
    let mut text = String::new();
    loop {
        typing.lines(&text);
        let prompt = if text.is_empty() { first } else { MORE };
        match editor.readline(prompt) {
            Ok(line) => match line.strip_suffix('\\') {
                Some(head) => {
                    text.push_str(head);
                    text.push('\n');
                }
                None if pasting() => {
                    text.push_str(&line);
                    text.push('\n');
                }
                None => {
                    text.push_str(&line);
                    let _ = editor.add_history_entry(text.as_str());
                    return Ok(Some(text));
                }
            },
            Err(ReadlineError::Interrupted) => {
                text.clear();
                println!("{}", style.dim("Ctrl+D or /exit quits."));
            }
            Err(ReadlineError::Eof) => return Ok(None),
            Err(e) => return Err(e.into()),
        }
    }
}

/// Streams the answer to `messages`, whose image parts are `images` in
/// order, reasoning dimmed, then one line of numbers. `stop` ends it early.
#[allow(clippy::too_many_arguments)]
fn answer(
    engine: &Engine,
    messages: &[Value],
    images: &[Vec<u8>],
    request: &Request,
    think: bool,
    style: &Style,
    raw: bool,
    stop: &AtomicBool,
) -> Result<Completion> {
    let mut prompt = engine.chat_prompt(messages, &options(think))?;
    prompt.images = images.to_vec();
    let mut out = io::stdout().lock();
    writeln!(out)?;
    let mut shown = Shown {
        markdown: Markdown::new(style.color && !raw),
        ..Shown::default()
    };
    let mut failed = None;
    let c = engine.complete(&prompt, request, &mut |part, _| {
        if let Err(e) = shown.show(&mut out, style, part) {
            failed = Some(e);
            return false;
        }
        !stop.load(Ordering::Relaxed)
    })?;
    if let Some(e) = failed {
        return Err(e.into());
    }
    shown.end_reasoning(&mut out, style)?;
    shown.markdown.finish(&mut out)?;
    Ok(c)
}

fn options(think: bool) -> Map<String, Value> {
    Map::from_iter([("enable_thinking".to_owned(), think.into())])
}

fn stopped(stop: &AtomicBool) -> bool {
    stop.load(Ordering::Relaxed)
}

/// Decode speed over the whole session.
#[derive(Default)]
struct Pace {
    generated: usize,
    decode: f64,
}

impl Pace {
    fn add(&mut self, c: &Completion) {
        self.generated += c.timings.generated;
        self.decode += c.timings.decode.as_secs_f64();
    }
}

// tokens per second, the only unit this project answers to
fn rate(n: usize, seconds: f64) -> f64 {
    if seconds > 0.0 {
        n as f64 / seconds
    } else {
        0.0
    }
}

const BAR: usize = 16;
const DIM: &str = "38;2;167;159;176";
const BRIGHT: &str = "1;38;2;232;228;236";

/// The line under an answer: what it took on the left, how full the context
/// is and how fast answers come after it.
fn numbers(style: &Style, c: &Completion, pace: &Pace, context: usize, stopped: bool) -> String {
    let t = &c.timings;
    let mut left = format!(
        "{} tokens    first token {:.2} s",
        c.completion_tokens,
        t.prefill.as_secs_f64()
    );
    if t.cached_tokens > 0 {
        left += &format!("    {} reused", tokens(t.cached_tokens));
    }
    if stopped {
        left += "    stopped";
    }

    let used = (c.prompt_tokens + c.completion_tokens).min(context);
    let fill = (used * BAR).div_ceil(context.max(1));
    let percent = format!(" {}%", (used * 100).div_ceil(context.max(1)));
    let last = format!("{:.0} t/s", rate(t.generated, t.decode.as_secs_f64()));
    let avg = format!("{:.0} t/s", rate(pace.generated, pace.decode));
    let width = columns().unwrap_or(usize::MAX);
    // in a narrow window the bar goes first, then the gap, the average and
    // the context, so the numbers stay on one line
    let fits = |bar: bool, gap: usize, avg_shown: bool, context_shown: bool| {
        let mut n = left.chars().count() + gap + "last ".len() + last.len();
        if context_shown {
            n += "context".len() + percent.len() + "    ".len();
            if bar {
                n += 1 + BAR;
            }
        }
        if avg_shown {
            n += "    avg ".len() + avg.len();
        }
        n < width
    };
    let (bar, gap, avg_shown, context_shown) = [
        (true, 8, true, true),
        (false, 8, true, true),
        (false, 4, true, true),
        (false, 4, false, true),
        (false, 4, false, false),
    ]
    .into_iter()
    .find(|&(b, g, a, c)| fits(b, g, a, c))
    .unwrap_or((false, 4, false, false));
    let mut parts = Vec::new();
    if context_shown {
        parts.push((DIM, "context".to_owned()));
        if bar {
            parts.push((DIM, " ".to_owned()));
            parts.push(("38;2;220;213;226", "━".repeat(fill)));
            parts.push(("38;2;62;57;68", "━".repeat(BAR - fill)));
        }
        parts.push((BRIGHT, percent));
        parts.push((DIM, "    ".to_owned()));
    }
    parts.push((DIM, "last ".to_owned()));
    parts.push((BRIGHT, last));
    if avg_shown {
        parts.push((DIM, "    avg ".to_owned()));
        parts.push((BRIGHT, avg));
    }
    let right: String = parts
        .iter()
        .map(|(code, text)| style.paint(code, text))
        .collect();
    // no padding to the edge: the terminal rewraps padded lines on resize
    format!("{}{}{right}", style.dim(&left), " ".repeat(gap))
}

/// What has gone to the terminal so far: whitespace before the first word
/// of each part is held back, and reasoning runs in its own style.
#[derive(Default)]
struct Shown {
    started: bool,
    in_reasoning: bool,
    markdown: Markdown,
}

impl Shown {
    fn show(&mut self, out: &mut impl Write, style: &Style, part: &Split) -> io::Result<()> {
        if !part.reasoning.is_empty() {
            let text = self.trim(&part.reasoning);
            if !text.is_empty() && !self.in_reasoning {
                out.write_all(style.reasoning_start().as_bytes())?;
                self.in_reasoning = true;
            }
            out.write_all(text.as_bytes())?;
        }
        if !part.content.is_empty() {
            if self.in_reasoning {
                self.end_reasoning(out, style)?;
                out.write_all(b"\n\n")?;
                self.started = false;
            }
            let text = self.trim(&part.content);
            self.markdown.write(out, text)?;
        }
        out.flush()
    }

    fn trim<'t>(&mut self, text: &'t str) -> &'t str {
        if self.started {
            return text;
        }
        let text = text.trim_start();
        self.started = !text.is_empty();
        text
    }

    fn end_reasoning(&mut self, out: &mut impl Write, style: &Style) -> io::Result<()> {
        if self.in_reasoning {
            out.write_all(style.reset().as_bytes())?;
            self.in_reasoning = false;
        }
        Ok(())
    }
}

/// The colours of the Kinetic mark, or none when stdout is not a terminal
/// or `NO_COLOR` is set.
#[derive(Clone, Copy)]
struct Style {
    color: bool,
}

impl Style {
    fn detect() -> Self {
        Style {
            color: io::stdout().is_terminal()
                && std::env::var_os("NO_COLOR").is_none()
                && enable_escapes(),
        }
    }

    fn paint(&self, code: &str, text: &str) -> String {
        if self.color {
            format!("\x1b[{code}m{text}\x1b[0m")
        } else {
            text.to_owned()
        }
    }

    fn accent(&self, text: &str) -> String {
        self.paint("1;38;2;226;172;128", text)
    }

    fn bright(&self, text: &str) -> String {
        self.paint(BRIGHT, text)
    }

    fn dim(&self, text: &str) -> String {
        self.paint(DIM, text)
    }

    fn reasoning_start(&self) -> &'static str {
        if self.color {
            "\x1b[3;38;2;167;159;176m"
        } else {
            ""
        }
    }

    fn reset(&self) -> &'static str {
        if self.color {
            "\x1b[0m"
        } else {
            ""
        }
    }
}

/// The line editor's helper: colours the prompt and hands every edit to
/// Zero Wait.
struct Line<'t> {
    style: Style,
    typing: &'t Typing,
}

// rustyline counts escapes inside a prompt as columns, so the prompt is
// coloured here, where it knows to skip them
impl Highlighter for Line<'_> {
    fn highlight_prompt<'b, 's: 'b, 'p: 'b>(
        &'s self,
        prompt: &'p str,
        _default: bool,
    ) -> Cow<'b, str> {
        Cow::Owned(match prompt {
            PROMPT => self.style.accent(prompt),
            _ => self.style.dim(prompt),
        })
    }

    fn highlight_hint<'h>(&self, hint: &'h str) -> Cow<'h, str> {
        Cow::Owned(self.style.dim(hint))
    }
}

impl Completer for Line<'_> {
    type Candidate = String;

    fn complete(
        &self,
        line: &str,
        pos: usize,
        _ctx: &Context<'_>,
    ) -> rustyline::Result<(usize, Vec<String>)> {
        let names = commands_for(&line[..pos]).map(|(name, ..)| (*name).to_owned());
        Ok((0, names.collect()))
    }
}

impl Hinter for Line<'_> {
    type Hint = CommandHint;

    fn hint(&self, line: &str, pos: usize, _ctx: &Context<'_>) -> Option<CommandHint> {
        self.typing.line(line);
        if pos < line.len() {
            return None;
        }
        let (name, args, what) = commands_for(line).next()?;
        let rest = name[line.len()..].to_owned();
        Some(CommandHint {
            shown: format!("{rest}{args}   {what}"),
            rest,
        })
    }
}

impl Validator for Line<'_> {}

impl Helper for Line<'_> {}

/// Turns on escape sequences in the Windows console, which stays plain
/// text until a program asks.
#[cfg(windows)]
fn enable_escapes() -> bool {
    use windows_sys::Win32::System::Console::{
        GetConsoleMode, GetStdHandle, SetConsoleMode, ENABLE_VIRTUAL_TERMINAL_PROCESSING,
        STD_OUTPUT_HANDLE,
    };
    // SAFETY: console calls on this process's own stdout handle
    unsafe {
        let out = GetStdHandle(STD_OUTPUT_HANDLE);
        let mut mode = 0;
        GetConsoleMode(out, &mut mode) != 0
            && (mode & ENABLE_VIRTUAL_TERMINAL_PROCESSING != 0
                || SetConsoleMode(out, mode | ENABLE_VIRTUAL_TERMINAL_PROCESSING) != 0)
    }
}

#[cfg(not(windows))]
fn enable_escapes() -> bool {
    true
}

/// Whether more key presses are already waiting after Enter. The Windows
/// console delivers a paste as a burst of keys, line breaks as Enter, so a
/// line that ends with more keys behind it is part of one pasted message.
#[cfg(windows)]
fn pasting() -> bool {
    use windows_sys::Win32::System::Console::{
        GetStdHandle, PeekConsoleInputW, INPUT_RECORD, KEY_EVENT, STD_INPUT_HANDLE,
    };
    let waiting = || {
        // SAFETY: peeks at this process's own console input into a local buffer
        unsafe {
            let input = GetStdHandle(STD_INPUT_HANDLE);
            let mut records: [INPUT_RECORD; 16] = std::mem::zeroed();
            let mut n = 0;
            PeekConsoleInputW(input, records.as_mut_ptr(), records.len() as u32, &mut n) != 0
                && records[..n as usize]
                    .iter()
                    .any(|r| u32::from(r.EventType) == KEY_EVENT && r.Event.KeyEvent.bKeyDown != 0)
        }
    };
    // the rest of a paste can trail the first line by a few milliseconds
    waiting() || {
        std::thread::sleep(std::time::Duration::from_millis(15));
        waiting()
    }
}

// terminals elsewhere hand rustyline a paste whole, line breaks included
#[cfg(not(windows))]
fn pasting() -> bool {
    false
}

#[cfg(windows)]
fn columns() -> Option<usize> {
    use windows_sys::Win32::System::Console::{
        GetConsoleScreenBufferInfo, GetStdHandle, CONSOLE_SCREEN_BUFFER_INFO, STD_OUTPUT_HANDLE,
    };
    // SAFETY: the call fills the zeroed struct it is handed
    unsafe {
        let mut info: CONSOLE_SCREEN_BUFFER_INFO = std::mem::zeroed();
        (GetConsoleScreenBufferInfo(GetStdHandle(STD_OUTPUT_HANDLE), &mut info) != 0)
            .then(|| (info.srWindow.Right - info.srWindow.Left + 1) as usize)
    }
}

#[cfg(unix)]
fn columns() -> Option<usize> {
    // SAFETY: TIOCGWINSZ fills the zeroed winsize it is handed
    unsafe {
        let mut size: libc::winsize = std::mem::zeroed();
        (libc::ioctl(libc::STDOUT_FILENO, libc::TIOCGWINSZ, &mut size) == 0 && size.ws_col > 0)
            .then_some(size.ws_col as usize)
    }
}

/// A token count the way people read it: 32768 is 32k.
fn tokens(n: usize) -> String {
    if n >= 1024 && n.is_multiple_of(1024) {
        format!("{}k", n / 1024)
    } else {
        n.to_string()
    }
}

fn opening(system: Option<&str>) -> Vec<Value> {
    system
        .map(|s| json!({"role": "system", "content": s}))
        .into_iter()
        .collect()
}

/// A conversation read line by line from a pipe, answers to stdout.
fn plain(engine: &Engine, gen: &GenArgs) -> Result<()> {
    let request = gen.request(engine.default_sampling());
    let mut messages = opening(gen.system.as_deref());
    for line in io::stdin().lock().lines() {
        match line?.trim() {
            "" => {}
            "/exit" | "/quit" => break,
            "/clear" => messages = opening(gen.system.as_deref()),
            text => {
                messages.push(json!({"role": "user", "content": text}));
                let c = stream(engine, &messages, &request, None)?;
                messages.push(json!({"role": "assistant", "content": c.content}));
            }
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{commands_for, help, is_command, tokens, Shown, Style, COMMANDS};
    use kinetic_server::Split;

    #[test]
    fn pasted_text_starting_with_a_slash_is_a_message() {
        assert!(is_command("/thi"));
        assert!(is_command("/system be brief"));
        assert!(!is_command("//! Zero Wait in chat"));
        assert!(!is_command("/etc/hosts has a bad line"));
        assert!(!is_command("hello /think"));
    }

    #[test]
    fn commands_complete_until_a_space() {
        let names = |typed| commands_for(typed).map(|c| c.0).collect::<Vec<_>>();
        assert_eq!(names("/th"), ["/think"]);
        assert_eq!(names("/").len(), COMMANDS.len());
        assert!(names("/think on").is_empty());
        assert!(names("hello").is_empty());
        assert!(names("/vroom").is_empty());
        assert!(COMMANDS.iter().all(|(name, ..)| help().contains(name)));
    }

    fn part(reasoning: &str, content: &str) -> Split {
        Split {
            reasoning: reasoning.into(),
            content: content.into(),
        }
    }

    #[test]
    fn token_counts_read_naturally() {
        assert_eq!(tokens(32768), "32k");
        assert_eq!(tokens(4096), "4k");
        assert_eq!(tokens(1000), "1000");
    }

    #[test]
    fn leading_whitespace_is_held_back_once() {
        let style = Style { color: false };
        let mut out = Vec::new();
        let mut shown = Shown::default();
        for p in [part("", "\n\n"), part("", " Hi"), part("", "\n there")] {
            shown.show(&mut out, &style, &p).unwrap();
        }
        assert_eq!(String::from_utf8(out).unwrap(), "Hi\n there");
    }

    #[test]
    fn reasoning_comes_first_and_apart() {
        let style = Style { color: false };
        let mut out = Vec::new();
        let mut shown = Shown::default();
        for p in [part("\nhmm", ""), part("", "\nYes.")] {
            shown.show(&mut out, &style, &p).unwrap();
        }
        assert_eq!(String::from_utf8(out).unwrap(), "hmm\n\nYes.");
    }
}
