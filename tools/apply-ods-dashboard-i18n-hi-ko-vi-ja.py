#!/usr/bin/env python3
"""Apply the next ODS Dashboard i18n expansion: Hindi, Korean, Vietnamese, Japanese."""

from pathlib import Path
import subprocess

ROOT = Path.cwd()
I18N = ROOT / "ods/extensions/services/dashboard/src/i18n"

if not (I18N / "index.js").exists() or not (I18N / "en.js").exists():
    raise SystemExit("ERROR: apply the original ODS dashboard i18n contribution first.")

status = subprocess.run(
    ["git", "status", "--porcelain"], check=True, capture_output=True, text=True
).stdout.strip()
if status:
    raise SystemExit("ERROR: working tree is not clean.")

index = (I18N / "index.js").read_text(encoding="utf-8")
index = index.replace(
    "import es from './es'\nimport zhCN from './zh-CN'",
    "import es from './es'\nimport hi from './hi'\nimport ja from './ja'\nimport ko from './ko'\nimport vi from './vi'\nimport zhCN from './zh-CN'",
)
index = index.replace(
    "  {code: 'es', label: 'Español'},\n  {code: 'zh-CN', label: '简体中文'},",
    "  {code: 'es', label: 'Español'},\n  {code: 'hi', label: 'हिन्दी'},\n  {code: 'ja', label: '日本語'},\n  {code: 'ko', label: '한국어'},\n  {code: 'vi', label: 'Tiếng Việt'},\n  {code: 'zh-CN', label: '简体中文'},",
)
index = index.replace(
    "const dictionaries = {en, es, 'zh-CN': zhCN}",
    "const dictionaries = {en, es, hi, ja, ko, vi, 'zh-CN': zhCN}",
)
(I18N / "index.js").write_text(index, encoding="utf-8")

common = {
"hi": {
"language":"भाषा","back":"वापस","continue":"जारी रखें",
"welcome":"ODS में आपका स्वागत है।","welcomeBody":"लगभग एक मिनट में सेटअप पूरा करें। पहले owner card के audit trail के लिए एक लेबल दें।",
"setup":"सेटअप लेबल","user":"पहला उपयोगकर्ता कौन है?","userBody":"अंत में हम उसके लिए एक owner card बनाएँगे।",
"username":"उपयोगकर्ता नाम","stack":"अपना स्टैक चुनें।","stackBody":"आप इसे बाद में बदल सकते हैं।",
"chat":"केवल चैट","chatBody":"सिर्फ चैट इंटरफ़ेस।","agents":"चैट + Agents","agentsBody":"Hermes, वेब सर्च, उपयोग मॉनिटरिंग और n8n workflows जोड़ता है।",
"full":"पूरा ODS स्टैक","fullBody":"Agents, voice, RAG, research, privacy और observability जोड़ता है।","ready":"तैयार?","finish":"समाप्त करें",
"done":"सेटअप पूरा हो गया।","copy":"लिंक कॉपी करें","share":"साझा करें","dashboard":"डैशबोर्ड खोलें",
"identity":"आपकी पहचान","photo":"प्रोफ़ाइल फ़ोटो","upload":"फ़ोटो अपलोड करें","remove":"फ़ोटो हटाएँ","display":"प्रदर्शित नाम",
"save":"प्रोफ़ाइल सहेजें","saved":"प्रोफ़ाइल सहेजी गई।","access":"डैशबोर्ड एक्सेस","password":"डैशबोर्ड पासवर्ड बदलें","signout":"इस ब्राउज़र से साइन आउट करें"
},
"ja": {
"language":"言語","back":"戻る","continue":"続行",
"welcome":"ODSへようこそ。","welcomeBody":"約1分でセットアップできます。まず、オーナーカードの監査記録用ラベルを設定します。",
"setup":"セットアップラベル","user":"最初のユーザーは誰ですか？","userBody":"最後にそのユーザー用のオーナーカードを生成します。",
"username":"ユーザー名","stack":"スタックを選択してください。","stackBody":"後から変更できます。",
"chat":"チャットのみ","chatBody":"チャットだけを提供します。","agents":"チャット + Agents","agentsBody":"Hermes、Web検索、使用状況監視、n8nワークフローを追加します。",
"full":"ODSフルスタック","fullBody":"Agents、音声、RAG、リサーチ、プライバシー、可観測性を追加します。","ready":"準備はできましたか？","finish":"完了",
"done":"セットアップ完了です。","copy":"リンクをコピー","share":"共有","dashboard":"ダッシュボードを開く",
"identity":"あなたのプロフィール","photo":"プロフィール写真","upload":"写真をアップロード","remove":"写真を削除","display":"表示名",
"save":"プロフィールを保存","saved":"プロフィールを保存しました。","access":"ダッシュボードへのアクセス","password":"ダッシュボードのパスワードを変更","signout":"このブラウザーからサインアウト"
},
"ko": {
"language":"언어","back":"뒤로","continue":"계속",
"welcome":"ODS에 오신 것을 환영합니다.","welcomeBody":"약 1분이면 설정할 수 있습니다. 먼저 소유자 카드 감사 기록에 사용할 라벨을 정하세요.",
"setup":"설정 라벨","user":"첫 번째 사용자는 누구인가요?","userBody":"마지막에 해당 사용자의 소유자 카드를 생성합니다.",
"username":"사용자 이름","stack":"스택을 선택하세요.","stackBody":"나중에 변경할 수 있습니다.",
"chat":"채팅만","chatBody":"채팅 화면만 제공합니다.","agents":"채팅 + Agents","agentsBody":"Hermes, 웹 검색, 사용량 모니터링 및 n8n 워크플로를 추가합니다.",
"full":"전체 ODS 스택","fullBody":"Agents, 음성, RAG, 리서치, 개인정보 보호 및 관측성을 추가합니다.","ready":"준비되었나요?","finish":"완료",
"done":"설정이 완료되었습니다.","copy":"링크 복사","share":"공유","dashboard":"대시보드 열기",
"identity":"내 프로필","photo":"프로필 사진","upload":"사진 업로드","remove":"사진 삭제","display":"표시 이름",
"save":"프로필 저장","saved":"프로필이 저장되었습니다.","access":"대시보드 액세스","password":"대시보드 비밀번호 변경","signout":"이 브라우저에서 로그아웃"
},
"vi": {
"language":"Ngôn ngữ","back":"Quay lại","continue":"Tiếp tục",
"welcome":"Chào mừng đến với ODS.","welcomeBody":"Bạn có thể hoàn tất thiết lập trong khoảng một phút. Trước tiên, đặt nhãn cho nhật ký kiểm tra của thẻ chủ sở hữu.",
"setup":"Nhãn thiết lập","user":"Ai là người dùng đầu tiên?","userBody":"Cuối cùng chúng tôi sẽ tạo thẻ chủ sở hữu cho người đó.",
"username":"Tên người dùng","stack":"Chọn ngăn xếp của bạn.","stackBody":"Bạn có thể thay đổi sau.",
"chat":"Chỉ trò chuyện","chatBody":"Chỉ giao diện trò chuyện.","agents":"Trò chuyện + Agents","agentsBody":"Thêm Hermes, tìm kiếm web, giám sát sử dụng và quy trình n8n.",
"full":"Ngăn xếp ODS đầy đủ","fullBody":"Thêm Agents, thoại, RAG, nghiên cứu, quyền riêng tư và khả năng quan sát.","ready":"Sẵn sàng?","finish":"Hoàn tất",
"done":"Bạn đã hoàn tất.","copy":"Sao chép liên kết","share":"Chia sẻ","dashboard":"Mở dashboard",
"identity":"Danh tính của bạn","photo":"Ảnh hồ sơ","upload":"Tải ảnh lên","remove":"Xóa ảnh","display":"Tên hiển thị",
"save":"Lưu hồ sơ","saved":"Đã lưu hồ sơ.","access":"Quyền truy cập dashboard","password":"Đổi mật khẩu dashboard","signout":"Đăng xuất khỏi trình duyệt này"
}}

def dictionary(locale):
    d = common[locale]
    return f"""import en from './en'

export default {{
  ...en,
  'common.language': {d["language"]!r},
  'common.back': {d["back"]!r},
  'common.continue': {d["continue"]!r},
  'firstBoot.welcome.title': {d["welcome"]!r},
  'firstBoot.welcome.body': {d["welcomeBody"]!r},
  'firstBoot.setupLabel': {d["setup"]!r},
  'firstBoot.user.title': {d["user"]!r},
  'firstBoot.user.body': {d["userBody"]!r},
  'firstBoot.username': {d["username"]!r},
  'firstBoot.stack.title': {d["stack"]!r},
  'firstBoot.stack.body': {d["stackBody"]!r},
  'firstBoot.stack.chat.title': {d["chat"]!r},
  'firstBoot.stack.chat.blurb': {d["chatBody"]!r},
  'firstBoot.stack.agents.title': {d["agents"]!r},
  'firstBoot.stack.agents.blurb': {d["agentsBody"]!r},
  'firstBoot.stack.everything.title': {d["full"]!r},
  'firstBoot.stack.everything.blurb': {d["fullBody"]!r},
  'firstBoot.confirm.title': {d["ready"]!r},
  'firstBoot.confirm.finish': {d["finish"]!r},
  'firstBoot.done.title': {d["done"]!r},
  'firstBoot.done.copy': {d["copy"]!r},
  'firstBoot.done.share': {d["share"]!r},
  'firstBoot.done.dashboard': {d["dashboard"]!r},
  'profile.identity': {d["identity"]!r},
  'profile.photo': {d["photo"]!r},
  'profile.uploadPhoto': {d["upload"]!r},
  'profile.removePhoto': {d["remove"]!r},
  'profile.displayName': {d["display"]!r},
  'profile.save': {d["save"]!r},
  'profile.saved': {d["saved"]!r},
  'profile.dashboardAccess': {d["access"]!r},
  'profile.changePassword': {d["password"]!r},
  'profile.signOut': {d["signout"]!r},
}}
"""

for locale in common:
    (I18N / f"{locale}.js").write_text(dictionary(locale), encoding="utf-8")

test = (I18N / "index.test.js").read_text(encoding="utf-8")
test = test.replace(
    "expect(saveLanguage('zh-CN')).toBe('zh-CN')\n    expect(readLanguage()).toBe('zh-CN')",
    "expect(saveLanguage('hi')).toBe('hi')\n    expect(readLanguage()).toBe('hi')\n    expect(saveLanguage('ja')).toBe('ja')\n    expect(readLanguage()).toBe('ja')\n    expect(saveLanguage('ko')).toBe('ko')\n    expect(readLanguage()).toBe('ko')\n    expect(saveLanguage('vi')).toBe('vi')\n    expect(readLanguage()).toBe('vi')\n    expect(saveLanguage('zh-CN')).toBe('zh-CN')\n    expect(readLanguage()).toBe('zh-CN')",
)
test = test.replace(
    "expect(translate('zh-CN', 'profile.save')).toBe('保存个人资料')",
    "expect(translate('zh-CN', 'profile.save')).toBe('保存个人资料')\n    expect(translate('hi', 'profile.save')).toBe('प्रोफ़ाइल सहेजें')\n    expect(translate('ja', 'profile.save')).toBe('プロフィールを保存')\n    expect(translate('ko', 'profile.save')).toBe('프로필 저장')\n    expect(translate('vi', 'profile.save')).toBe('Lưu hồ sơ')",
)
test = test.replace(
    "['en', 'es', 'zh-CN']",
    "['en', 'es', 'hi', 'ja', 'ko', 'vi', 'zh-CN']",
)
(I18N / "index.test.js").write_text(test, encoding="utf-8")

check = subprocess.run(["git", "diff", "--check"], capture_output=True, text=True)
if check.returncode:
    print(check.stdout, check.stderr)
    raise SystemExit("ERROR: git diff --check failed.")

print("ODS Dashboard i18n expansion ready: hi, ja, ko, vi.")
print("No commit was created.")
