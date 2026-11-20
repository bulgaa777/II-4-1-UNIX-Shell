# Симуляторыг шалгах

Вебийг нээгээд команд оруулж **Ажиллуулах**, дараа нь **Дараах**-аар сүүлийн алхамд хүрнэ. Run нь дарааллыг бэлтгэдэг; Next нь алхмыг харуулдаг. Өмнөх командын файл дараагийн Run-д хадгалагдана. Файл дээр хулганаа аваачихад агуулга, нэрийн хажууд байтын хэмжээ харагдана. **Шинээр эхлэх** нь бүх виртуал файлыг сэргээнэ.

## MINOR-03 гар туршилт

Тохиолдол бүрийн өмнө **Шинээр эхлэх** дарна. Хос командуудын хооронд reset хийхгүй.

| Шалгалт | Дарааллаар оруулах команд | Хүлээгдэх үр дүн |
|---|---|---|
| Гаралт, оролт | `echo sample > out.txt`, `cat < out.txt` | Эхлээд stdout хоосон, файл 7 B. Дараа нь `sample`, exit 0. |
| Дахин бичих | `echo very-long-text > out.txt`, `echo x > out.txt`, `cat < out.txt` | Зөвхөн `x`, файл 2 B. Хуучин текстийн сүүл үлдэхгүй. |
| Гаралтгүй команд | `echo old > out.txt`, `true > out.txt` | Файл 0 B, stderr хоосон, exit 0. |
| Байхгүй команд + файл | `echo old > out.txt`, `no_such_cmd_xyz_123 > out.txt` | Файл 0 B, stderr-д `no_such_cmd_xyz_123: No such file or directory`, exit 127. |
| Програмын алдаа + файл | `cat missing.txt > out.txt` | out.txt үүсэж 0 B болно. `cat: missing.txt: No such file or directory`, exit 1. |
| Оролт нээх алдаа | `echo old > out.txt`, `cat > out.txt < missing.txt` | out.txt нь `old` ба newline-тойгоо, 4 B хэвээр. Алдаа `missing.txt: No such file or directory`, exit 1. |
| Нэг файл | `cat < names.txt > names.txt` | open(O_TRUNC)-ийн дараа унших тул names.txt 0 B, exit 0. |
| Буруу гаралтын зам | `echo hi > missing_dir/out.txt` | `missing_dir/out.txt: No such file or directory`, exit 1; файл үүсэхгүй. |
| Directory руу бичих | `echo hi > docs` | `docs: Is a directory`, exit 1; docs хэвээр. |
| Буруу синтакс | `echo hi >`, `echo hi > a > b`, `echo hi \|`, `\| wc -c` | Тус бүр parser-ийн алдаа, exit 2, child болон шинэ файл үүсэхгүй. |
| Хоосон оролт | Шинээр эхлээд input-ийг бүрэн арилган Run | stderr хоосон, child байхгүй, exit 0, prompt буцна. |
| Зөвхөн зай | Input-д 3 зай оруулж Run | Алдаа, child байхгүй, exit 0. |
| Pipe-ийн үр дүн | `no_such_cmd_xyz_123 \| wc -c` | stderr-д зүүн командын алдаа, stdout `0`, exit 0. Сүүлийн командын статусыг авна. |

Файл хоосрох мөчийг шалгахдаа `no_such_cmd_xyz_123 > out.txt`-ийн **open/dup2** алхам дээр зогсоно. execvp-ийн алдаа хараахан гараагүй байхад файл аль хэдийн **0 B** болсон байна. stderr нь fd 2 тул `>`-д орохгүй.

Хоосон мөр нь өмнөх статусыг хадгална: `false`, дараа нь хоосон оролт → exit 1 хэвээр. Зөвхөн зайтай мөр нь `execute()` рүү орж 0 буцаана. Энэ C хувилбар зайтай мөрийг history-д хадгалдаг: `echo first`, 3 зай, `!!` → `first` дахин гарахгүй.

## SUGGESTION-02 шалгах

- MN болон EN рүү сольж 3-р хэсгийн гарчигт “6 систем дуудлага” гэсэн буруу тоолол байхгүйг шалгана. Zombie нь төлөв, execvp нь сангийн интерфэйс гэж тайлбарласан.
- `sleep 3 &`-ийг алхамчилна: prompt → дуусалт/zombie → дараагийн давталтын reaping. Энэ нь бодит 3 секунд хэмжих тест биш. Бодит osh нь `getline()`-д хүлээж байвал дараагийн оролт иртэл цуглуулахгүй байж болно.
- `pwd`, `cd /tmp`, `pwd` ажиллуулна. `cd` нь exit 127, хоёр pwd ижил. Хүүхдийн chdir() эцгийн хавтсыг солихгүй гэсэн тайлбарыг шалгана.
- Хамгаалалтын асуултуудаас файл хоосрох, 127, zombie, cd, системийн дуудлагын картын асуултыг нээж тайлбарыг шалгана.
- Prev/Next/Play, keyboard сум, Reset, MN/EN, theme-ийг туршина. 390 px өргөнд хуудас баруун тийш хальж байгаа эсэхийг шалгана.

## Автомат тестийг давтах

Node.js 20+ дээр dependency суулгахгүй:

```bash
node tests/test_simulator.cjs
```

Linux/macOS/WSL дээр Node.js, C11 compiler, Python 3-тай бол:

```bash
node tests/test_simulator.cjs --compare-c
cc -std=c11 -Wall -Wextra -O2 src/osh.c -o osh
python3 tests/test_shell.py
```

Parity тест нь түр хавтаст ижил файлууд үүсгээд simulator ба бодит C shell-ийн stdout, stderr, exit code, файлын агуулгыг харьцуулна. Түүх болон хоосон мөрийг тусдаа интерактив session-оор шалгана. Тестийн дараа зөвхөн өөрийн үүсгэсэн түр файлуудаа цэвэрлэнэ. Background-ийн timeline нь загварын шалгалт; OS scheduler-тэй адил хугацаа гэж үзэхгүй.

GitHub → Actions → **Simulator and C parity** → ногоон run → **test-evidence**-ээс дахин туршилтын лог татаж болно.

## Screenshot

Шинэ нотолгоо нь `docs/screenshots/virtualbox/` дотор байна. `00-ubuntu-tests.png`, `01-real-c-shell-edge-cases.png` нь бодит Ubuntu VM-ийн терминал; `02`–`08` нь тэр VM-ийн Firefox доторх симулятор. Браузерын PID, файлууд нь сургалтын загварын өгөгдөл хэвээр.

`09-narrow-layout.png` нь Ubuntu доторх headless Firefox-ийн 500 px өргөнтэй харагдац. Энэ орчинд Firefox цонхны өргөнийг 390 px болгох хүсэлтийг 500 px-ээр хязгаарласан тул 390 px гэж тайлагнаагүй. Бодит хэмжээг `docs/evidence/virtualbox/browser-checks.json`-д хадгалсан.

VM-ийн орчин, файлын SHA256, 70/16 тестийн лог нь `docs/evidence/virtualbox/` дотор. Өмнөх Windows зургуудыг `docs/screenshots/legacy-windows/` руу архивласан. Тайланд шинэ `virtualbox/` зургуудыг хэрэглэнэ. Зургийн жагсаалтыг [REVIEW_RESPONSES.md](REVIEW_RESPONSES.md)-ээс үзнэ.
