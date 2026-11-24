# CS222 — Beamer deck (Prompting & PEFT)

Bản Beamer của `source/slide-cs222.pptx.pdf`: **slide 1–55 đúng thứ tự và đúng câu chữ gốc**, cộng chương 4 (slide 56–73) về kết quả tái lập trong repo
(kể cả các lỗi chính tả như "Downsteam", "Adaption"), chỉ đổi cách trình bày.
Các slide gốc chỉ có hình thì ở đây có tiêu đề + caption ghi nguồn hình.

## Cấu trúc

```
main_uit.tex          theme, metadata, footer, gọi các phần (file chính duy nhất)
parts/
  00_title.tex        slide 1–2   (bìa, nội dung)
  01_dta.tex          slide 3–15  (1. Bài toán Downstream Task)
  02_gepa.tex         slide 16–32 (2. GEPA)
  03_t2l.tex          slide 33–54 (3. Text-to-LoRA)
  04_cost.tex         slide 55    (Chi phí và hạn chế)
  05_experiments.tex  chương 4: thực nghiệm & kết hợp T2L + GEPA (số liệu từ docs/report)
  06_references.tex   rỗng — deck gốc không có slide tài liệu tham khảo
figure/deck/          ảnh lấy nguyên từ slide gốc (pdfimages + cắt viền trắng)
figure/t2l, gepa/     hình và bảng tách từ paper (vector, không phải ảnh chụp)
source/               3 file PDF gốc (đề bài, paper T2L, paper GEPA)
tools/crop_figures.py sinh lại toàn bộ figure/ từ source/*.pdf
```

## Biên dịch

```bash
make          # tách lại hình + xelatex 2 lần
make figures  # chỉ tách hình
make zip      # overleaf_uit.zip (main_uit.tex, parts/, fonts/, figure/)
```

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
- Slide 52 dùng Bảng 1 dạng vector từ paper; slide 53, 54 dùng ảnh bảng của slide gốc (bản crop Bảng 3 cũ bị cắt mất cột).
