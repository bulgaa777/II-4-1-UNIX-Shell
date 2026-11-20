# Reviewer responses — Ч. Мөнхбаяр

| ID | Шийдвэр | Өөрчлөлт | Нотлох тест |
|---|---|---|---|
| MINOR-03 | Зөвшөөрсөн | Гаралтын файлыг open үед нь үүсгэж/хоосолно. exec алдаа, програмын алдаа, оролт/гаралтын алдаа, хоосон/зайтай мөрийг C кодтой тааруулсан. stderr болон exit code тусдаа. | `tests/test_simulator.cjs`: stdout/stderr/code/file харьцуулалт, truncation snapshot, интерактив history, blank/whitespace, pipeline. |
| SUGGESTION-02 | Зөвшөөрсөн | Гарчгаас буруу “6 систем дуудлага”-ыг хассан. Zombie төлөв, execvp сангийн интерфэйс, background reaping, getline хүлээлт, parent cd, 127-ийн тайлбарыг зассан. MN/EN хамгаалалтын асуулт нэмсэн. | Bilingual content regression; браузерт карт, background, cd, quiz, theme, reset шалгах. |

Симулятор нь сургалтын загвар. C shell-ийн хязгаарлалтыг өөр shell-ийн дүрмээр солиогүй. Суурь C код өөрчлөгдвөл `src/osh.c`, embedded код, model болон тестийг хамт шинэчлэх шаардлагатай.

## Дахин туршилт — 2026-11-20

- Windows: Node.js 24.11.1, 70 simulator шалгалт PASS.
- GitHub Actions: Ubuntu 26.04.1, Node.js 22.23.4, C11 compiler; **70 simulator checks (C parity enabled)** болон **16 C shell tests** PASS. [Баталгаажсан run](https://github.com/mubabne/osh-interactive-simulator/actions/runs/44740359393).
- Parity шалгалтаар 44 нэг команд, 5 файлтай scenario, 7 интерактив session-ийг бодит C shell-тэй stdout/stderr/exit code/файлаар харьцуулсан. Үлдсэн шалгалтууд нь snapshot, reset, background загвар, тайлбарын regression.
- [Simulator лог](evidence/simulator-results.txt), [C shell лог](evidence/c-shell-results.txt), [өмнөх/дараах JSON](evidence/before-after.json).
- Браузер: Chrome, desktop болон 390 × 844 viewport. Хуудас бүхлээрээ баруун тийш хальсангүй; навигац өөрийн horizontal scroll-той. MN/EN, theme, reset, keyboard алхам, background prompt, шинэ quiz тайлбарыг шалгасан.
- [Live Vercel](https://osh-interactive-simulator.vercel.app/). Веб нь нийтэд нээлттэй; source repo private.

## Өмнөх/дараах

| Нөхцөл | Өмнөх симулятор | Зассан симулятор |
|---|---|---|
| Зөвхөн зай | `Missing command` | Алдаагүй, child үүсэхгүй |
| Байхгүй команд + шинэ output | Файл үүсэхгүй | 0 B файл, stderr алдаа, exit 127 |
| Байхгүй команд + байсан output | Хуучин агуулга үлдэнэ | open үед 0 B болно |
| Байхгүй хавтас руу output | Виртуал файл буруу үүсгэнэ | open алдаа, файл үүсэхгүй |
| Directory руу output | Directory-г текстээр дарна | `Is a directory`, directory хэвээр |
| Input нээх алдаа + output | Хуучин output хэвээр | Өмнөх зөв ажиллагааг хадгалсан |

Өмнөх үр дүнг эх багийн `1154e60` commit-ийн HTML-ээс ажиллуулж авсан. JSON-ийг `tests/compare_before.cjs` үүсгэсэн; таамгаар бичээгүй.

## Screenshot-ийн тайлбар

Зургууд нь ажиллаж буй браузераас авсан. Файл, PID, лог нь симуляторын виртуал өгөгдөл; OS-оос шууд хэмжсэн screenshot гэж тайлбарлахгүй.

| Зураг | Тайланд хэрэглэх тайлбар |
|---|---|
| `screenshots/01-vercel-deployed.jpg` | Vercel production deployment амжилттай. |
| `screenshots/02-failed-command-truncation.jpg` | Команд олдохгүй ч output 0 B болсон; stderr ба exit 127. |
| `screenshots/03-missing-input-preserves-output.jpg` | Input нээх алдаа, exit 1; output өмнөх 4 B хэвээр. |
| `screenshots/04-whitespace-no-error.jpg` | Зөвхөн зайтай оролт алдаагүй, exit 0. |
| `screenshots/05-empty-input-no-child.jpg` | Хоосон оролт шинэ child үүсгэхгүй, exit 0. |
| `screenshots/06-background-prompt.jpg` | Background child ажиллаж байхад prompt буцсан загварын алхам. |
| `screenshots/07-concepts-mn.jpg` | Зассан гарчиг, execvp болон zombie-ийн ялгаа. |
| `screenshots/08-defense-quiz-en.jpg` | Файл exec-ээс өмнө хоосордог тухай хамгаалалтын асуулт. |
| `screenshots/09-mobile-layout.jpg` | 390 × 844 хэмжээний симуляторын харагдац. |

Тайланд 02, 03, 07 зургийг сонгоход үндсэн хоёр review саналын нотолгоо харагдана.

## Үлдсэн хязгаарлалт

Бүх UNIX программ, option, permission, signal, scheduler-ийг загварчлаагүй. Background animation нь бодит цагийн туршилт биш. C baseline-ийн quoted operator, нэг pipe, built-in cd байхгүй зэрэг хязгаарлалтыг хэвээр хадгалсан. Шинэ C засвар нэгтгэвэл parity-г дахин ажиллуулна.
