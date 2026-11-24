# CS222 — Beamer deck (Prompting & PEFT)

Bản Beamer của `source/slide-cs222.pptx.pdf`: **toàn bộ 55 slide gốc giữ nguyên thứ tự và câu chữ**, tiếp theo là chương 4 gồm **11 slide nội dung chính + 1 slide demo + 4 slide appendix**
(kể cả các lỗi chính tả như "Downsteam", "Adaption" ở phần gốc), chỉ đổi cách trình bày.
Chương 4 dành khoảng 20–22 phút cho số liệu và 8–10 phút cho demo. Các slide gốc chỉ có hình thì ở đây có tiêu đề + caption ghi nguồn hình.

## Cấu trúc

```
main_uit.tex          theme, metadata, footer, gọi các phần (file chính duy nhất)
parts/
  00_title.tex        không dùng bởi main_uit (bìa/agenda nằm inline)
  01_dta.tex          slide 3–15  (1. Bài toán Downstream Task)
  02_gepa.tex         slide 16–41 (2. GEPA)
  03_t2l.tex          slide 42–63 (3. Text-to-LoRA)
  04_cost.tex         slide 64    (Chi phí và hạn chế)
  05_experiments.tex  chương 4: slide 65–81 (phân tích, demo và 4 appendix Q&A)
  06_references.tex   rỗng — deck gốc không có slide tài liệu tham khảo
figure/deck/          ảnh lấy nguyên từ slide gốc (pdfimages + cắt viền trắng)
figure/t2l, gepa/     hình và bảng tách từ paper (vector, không phải ảnh chụp)
source/               3 file PDF gốc (đề bài, paper T2L, paper GEPA)
tools/crop_figures.py sinh lại toàn bộ figure/ từ source/*.pdf
```

### Mạch chương 4

- Thiết lập, so với paper, case study lỗi định dạng WinoGrande.
- T2L theo paired CI, GEPA so với ICL3, token/wall-time cost.
- Ba cách kết hợp, pipeline đồng tối ưu, kết quả và biến động giữa hai lần search.
- Demo AdaptLab theo một câu WinoGrande và prompt history thật; không mô phỏng search khi endpoint lỗi.
- Appendix giữ bảng 6 phiên bản, protocol GEPA chi tiết, kiểm chứng harness và giới hạn.

Số headline dùng run chuẩn `mistral-7b-v1` trong `docs/report/mistral-api-v1/`.
Các phân tích chỉ có ở lần chạy trước được ghi rõ `Run A` và lấy từ
`docs/report/t2l-gepa-comparison.md` hoặc `docs/report/mistral/report.md`.

Trạng thái demo (kiểm tra 24/11/2026): `https://cs222.lethienquan.site` trả **HTTP 502**.
Không dùng screenshot giả. Fallback:
- Prompt history và kết quả per-item: `/data/quan.lt/temp/t2l-mistral/artifacts/mistral-7b-v1/`.
- Cách chạy local và endpoint: xem `docs/demo.md`.

`main_uit.pdf` hiện có 81 trang; `main.pdf` cũ không phải bản master.

## Biên dịch

```bash
make          # tách lại hình + xelatex 2 lần
make figures  # chỉ tách hình
make zip      # overleaf_uit.zip (main_uit.tex, parts/, fonts/, figure/)
```

Trên Linux không có TeX hệ thống, bản hiện tại đã được kiểm tra bằng Tectonic 0.15.0
(đặt trong `.tools/`, gitignored) với cache project-local. `make` giữ đường dẫn BasicTeX
trên macOS như lịch sử dự án; có thể override `XELATEX` khi cần.

Yêu cầu: XeLaTeX (TeX Live 2026 / BasicTeX). Gói cần cài trên BasicTeX:

```bash
sudo tlmgr install babel-vietnamese
```

(Các gói còn lại — beamer, tikz, booktabs, hyperref, xcolor, fontspec, graphicx — BasicTeX đã có.)

## Đưa lên Overleaf

1. `make zip`
2. Overleaf → New Project → Upload Project → chọn `overleaf_uit.zip`
3. Menu → Compiler → **XeLaTeX** → Recompile

File dùng đường dẫn tương đối, font mặc định của TeX Live, tên file ASCII thuần
— không phụ thuộc máy macOS.

## Ghi chú

- `figure/deck/` là ảnh lấy từ `source/slide-cs222.pptx.pdf`, không do script sinh ra.
- `figure/t2l`, `figure/gepa` được tạo tự động; đừng sửa tay, sửa toạ độ trong `tools/crop_figures.py` rồi chạy `make figures`.
- Trang 61–63 dùng bảng T2L: trang 61 dùng Bảng 1 dạng vector từ paper; trang 62–63 dùng
  ảnh bảng của slide gốc (bản crop Bảng 3 cũ bị cắt mất cột).
