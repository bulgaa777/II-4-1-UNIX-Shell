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
- Анхны браузерын шалгалт: Windows Chrome, desktop болон 390 × 844 viewport. Хуучин зургууд `screenshots/legacy-windows/` дотор хадгалагдсан.
- **Бодит VM-ийн дахин туршилт:** хэрэглэгчийн `ubuntu` VirtualBox VM; Ubuntu 24.04.4 LTS, kernel 7.0.0-42-generic, x86_64, X11; 4 GB RAM, 2 vCPU. GCC 13.3.0, Node.js 22.23.1, Python 3.12.3. **70 simulator/C parity шалгалт, 16 C shell тест PASS.** [Орчин ба SHA256](evidence/virtualbox/environment.json), [simulator лог](evidence/virtualbox/simulator-results.txt), [C лог](evidence/virtualbox/c-shell-results.txt).
- VM-ийн Firefox 147.0.3 дээр live Vercel хуудасны redirection, алдаа, хоосон/зайтай оролт, background, MN/EN тайлбар, quiz-ийг шалгаж зураг авсан. [Браузерын үр дүн](evidence/virtualbox/browser-checks.json).
- Ubuntu Firefox-ийн нарийн цонхны бодит өргөн 500 px, өндөр 758 px, document өргөн 488 px байсан. Firefox 390 px хүсэлтийг 500 px-ээр хязгаарласан. Энэ VM дээр 390 px mobile шалгалт хийсэн гэж үзээгүй.
- GCC build амжилттай. Суурь C кодын `write()`-ийн буцаах утгыг үл тоосон warning хэвээр; [build лог](evidence/virtualbox/build.txt). Энэ нь SUGGESTION-03-ын тусдаа ажил.
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

Үндсэн шинэ зургуудыг хэрэглэгчийн ажиллаж буй Ubuntu VM-ээс авсан. `00`, `01` нь бодит C программын гаралт; `02`–`08` нь Ubuntu Firefox доторх сургалтын симулятор. Тэдгээр браузерын файл, PID, лог нь виртуал загварын өгөгдөл. `09`-ийг Ubuntu доторх headless Firefox-оос авсан.

| Зураг | Тайланд хэрэглэх тайлбар |
|---|---|
| `screenshots/virtualbox/00-ubuntu-tests.png` | Ubuntu VM дотор 70 parity шалгалт, 16 C тест давсан. |
| `screenshots/virtualbox/01-real-c-shell-edge-cases.png` | Бодит C shell: truncate, input алдаа, хоосон/зайтай оролтын exit code ба файлын хэмжээ. |
| `screenshots/virtualbox/02-failed-command-truncation.png` | Ubuntu Firefox: команд олдохгүй ч output 0 B; stderr ба exit 127. |
| `screenshots/virtualbox/03-missing-input-preserves-output.png` | Input нээх алдаа, exit 1; output өмнөх 4 B хэвээр. |
| `screenshots/virtualbox/04-whitespace-no-error.png` | Зөвхөн зайтай оролт алдаагүй, exit 0. |
| `screenshots/virtualbox/05-empty-input-no-child.png` | Хоосон оролт шинэ child үүсгэхгүй, exit 0. |
| `screenshots/virtualbox/06-background-prompt.png` | Background child ажиллаж байхад prompt буцсан загварын алхам. |
| `screenshots/virtualbox/07-concepts-mn.png` | Зассан гарчиг, execvp болон zombie-ийн ялгаа. |
| `screenshots/virtualbox/08-defense-quiz-en.png` | Файл exec-ээс өмнө хоосордог тухай хамгаалалтын асуулт. |
| `screenshots/virtualbox/09-narrow-layout.png` | Ubuntu Firefox-ийн 500 px өргөнтэй нарийн харагдац. |

Тайланд `00`, `01`, `02`, `07`-оос сонгож болно. Өмнөх Vercel deployment-ийн зураг нь `screenshots/legacy-windows/01-vercel-deployed.jpg`; энэ нь VM туршилтын зураг биш.

## Үлдсэн хязгаарлалт

Бүх UNIX программ, option, permission, signal, scheduler-ийг загварчлаагүй. Background animation нь бодит цагийн туршилт биш. C baseline-ийн quoted operator, нэг pipe, built-in cd байхгүй зэрэг хязгаарлалтыг хэвээр хадгалсан. Шинэ C засвар нэгтгэвэл parity-г дахин ажиллуулна.
