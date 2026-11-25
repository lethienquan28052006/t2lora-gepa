# Speaker notes — Prompting & PEFT

Tài liệu này khớp với `slides/main_uit.pdf` hiện tại: **76 trang**, chương 4 ở trang 65–76.
Mỗi mục tương ứng một trang PDF. Thời lượng là gợi ý cho một buổi seminar khoảng 80–85 phút.

**Cách dùng nhanh**

- **Lời nói** là bản nháp để nói tự nhiên, không cần đọc nguyên văn.
- **Nhấn** là ý hoặc con số phải khớp slide.
- **Chuyển** là câu nối sang trang sau.
- Các từ viết tắt: DTA = Downstream Task Adaptation; HN = hypernetwork; ICL = in-context learning.

## Nhịp tổng thể

| Phần | Trang | Thời lượng gợi ý |
|---|---:|---:|
| Mở đầu | 1–2 | 2 phút |
| Chương 1 — Bài toán DTA | 3–15 | 12–14 phút |
| Chương 2 — GEPA | 16–41 | 20–22 phút |
| Chương 3 — Text-to-LoRA | 42–64 | 16–18 phút |
| Chương 4 — Thực nghiệm, kết hợp và demo | 65–76 | 30 phút |
| **Tổng** | **76** | **80–86 phút** |

Nếu thiếu thời gian, giữ nguyên chương 4; rút gọn các slide công trình liên quan ở chương 2 và phần module kỹ thuật ở chương 3.

---

# Mở đầu

### Trang 1 — Bìa · 1,5 phút

**Lời nói:** Kính chào thầy/cô và các bạn. Nhóm 5 trình bày seminar CS222 với chủ đề Prompting và PEFT. Phần ứng dụng của nhóm đi từ bài toán thích nghi mô hình xuống hai họ phương pháp: tối ưu prompt với GEPA và thích nghi trọng số hiệu quả với Text-to-LoRA. Cuối cùng nhóm ghép hai hướng này trên cùng một thực nghiệm để xem chúng bổ sung hay cạnh tranh nhau.

**Nhấn:** Tên nhóm, tên đề tài, và cấu trúc “một bài toán — hai bề mặt thích nghi — một thực nghiệm chung”.

**Chuyển:** “Nhóm em xin điểm nhanh bốn phần của bài trình bày.”

### Trang 2 — Nội dung · 30 giây

**Lời nói:** Bài trình bày có bốn phần: bài toán downstream task, GEPA cho tối ưu prompt, Text-to-LoRA cho thích nghi trọng số, và cuối cùng là quy trình thực nghiệm cùng kết quả kết hợp hai phương pháp. Hai phương pháp đầu là nền tảng lý thuyết; phần thực nghiệm ở cuối mới là phần nhóm tự chạy và kiểm chứng.

**Nhấn:** Đây là bốn bước logic, không phải bốn chủ đề rời nhau.

**Chuyển:** “Bắt đầu từ câu hỏi gốc: thích nghi một mô hình cho task mới thực chất là làm gì?”

---

# Chương 1 — Bài toán Downstream Task

### Trang 3 — Divider chương 1 · 15 giây

**Lời nói:** Chương 1 đặt ngôn ngữ chung cho cả bài: thế nào là thích nghi một mô hình cho downstream task, và chúng ta có thể can thiệp vào đâu trong quá trình đó.

**Nhấn:** Ba mục: giới thiệu bài toán, các phương pháp, và hạn chế.

**Chuyển:** “Bắt đầu bằng cách viết mô hình dưới dạng một hàm của prompt và trọng số.”

### Trang 4 — Mô hình và hai bề mặt thích nghi · 60–75 giây

**Lời nói:** Gọi mô hình là M với bộ trọng số ban đầu θ₀. Với một đầu vào x, đầu ra không chỉ phụ thuộc vào trọng số mà còn phụ thuộc vào prompt π. Vì vậy có thể viết đầu ra là M(x; π, θ₀ + Δθ). Δθ là phần cập nhật trọng số, còn π là phần điều khiển ở không gian văn bản.

**Nhấn:** Hai bề mặt thích nghi: **prompt π** và **trọng số Δθ**. Mọi phương pháp trong bài đều tác động vào một trong hai, hoặc cả hai.

**Chuyển:** “Vậy mục tiêu của downstream task adaptation là tìm π và Δθ như thế nào?”

### Trang 5 — Định nghĩa DTA · 80–90 giây

**Lời nói:** Downstream task adaptation là điều chỉnh mô hình M để làm tốt task T thay vì huấn luyện lại từ đầu. Tập dữ liệu D_T gồm các cặp (x, m), trong đó x là input và m là đáp án đúng. Về mặt tối ưu, ta tìm cặp (π*, Δθ*) để kỳ vọng của metric μ trên dữ liệu task là lớn nhất. Nói ngắn gọn: tìm cách hỏi tốt nhất và bộ trọng số phù hợp nhất cho task.

**Nhấn:** Công thức argmax có hai biến, không phải chỉ một. Đây là lý do có thể tối ưu prompt, tối ưu trọng số, hoặc ghép cả hai.

**Chuyển:** “Một vài ví dụ sẽ làm rõ x, m và μ trông như thế nào.”

### Trang 6 — Ví dụ downstream task · 30 giây

**Lời nói:** Downstream task rất đa dạng: giải toán, hỏi đáp nhiều bước, kiểm chứng thông tin, tuân thủ chỉ dẫn phức tạp, tối ưu mã nguồn. Điểm chung là mỗi task có cách sinh input, dạng đáp án và metric riêng. Vì vậy cùng một mô hình có thể rất mạnh ở task này nhưng yếu ở task khác nếu không thích nghi.

**Nhấn:** Không có một prompt vạn năng cho mọi task.

**Chuyển:** “Ba ví dụ cụ thể ở bảng sau cho thấy đáp án và cách đánh giá khác nhau ra sao.”

### Trang 7 — Input, đáp án và metric · 60 giây

**Lời nói:** Với giải toán như GSM8K, input là đề bằng ngôn ngữ tự nhiên, đáp án gồm lời giải và đáp số; cách đánh giá thường là exact match ở đáp số cuối. Với HotpotQA, mô hình nhận câu hỏi và kho tài liệu, phải tổng hợp nhiều bước; metric là EM hoặc F1. Với kiểm chứng thông tin như HoVer, mô hình nhận phát biểu và bằng chứng, trả nhãn supported/not, đo bằng accuracy hoặc macro-F1.

**Nhấn:** Metric quyết định “thế nào là trả lời đúng”; tối ưu mù metric rất dễ tối ưu sai thứ.

**Chuyển:** “Trong thực tế, một bài toán thường không chỉ có một LLM mà là cả một hệ thống.”

### Trang 8 — Compound AI System · 50–60 giây

**Lời nói:** Hình này minh họa một compound AI system: nhiều module LLM nối tiếp, mỗi module có một prompt riêng và đầu ra của module trước là đầu vào của module sau. Nếu chỉnh prompt ở một module, lỗi có thể lan sang các module phía sau, nên tối ưu thủ công toàn hệ thống rất khó. Đây là lý do cần các phương pháp tối ưu tự động ở cấp hệ thống, không chỉ cấp một prompt đơn lẻ.

**Nhấn:** Độ phức tạp tăng theo số module và theo đường lan truyền lỗi.

**Chuyển:** “Có hai họ cách can thiệp: tối ưu prompt và tối ưu trọng số.”

### Trang 9 — Tối ưu prompt bằng ICL · 40–50 giây

**Lời nói:** Hướng thứ nhất là giữ nguyên trọng số và thay đổi cách hỏi. In-context learning đưa ví dụ hoặc chỉ dẫn vào prompt: few-shot, chain-of-thought, self-consistency, tree-of-thoughts. Những kỹ thuật này hiệu quả nhưng chủ yếu dựa vào kinh nghiệm của người viết prompt.

**Nhấn:** ICL không cập nhật mô hình; nó thay đổi điều kiện đầu vào.

**Chuyển:** “Khi viết tay không còn đủ, ta chuyển sang tối ưu prompt tự động.”

### Trang 10 — Tối ưu prompt tự động · 60 giây

**Lời nói:** Có bốn nhóm chính. LLM-as-an-optimizer dùng chính LLM để đề xuất prompt. EvoPrompt dùng thuật toán tiến hóa. RL-based prompting huấn luyện một mô hình nhỏ sinh token prompt để tối đa phần thưởng. Và với compound AI system, các framework như DSPy hoặc MIPROv2 tối ưu đồng thời instruction và few-shot cho nhiều module.

**Nhấn:** Điểm chuyển từ “viết prompt” sang “tìm prompt bằng thuật toán”.

**Chuyển:** “Hướng còn lại là thay đổi trọng số, nhưng với chi phí thấp hơn full fine-tuning.”

### Trang 11 — Tối ưu tham số và PEFT · 60 giây

**Lời nói:** Full fine-tuning cập nhật toàn bộ trọng số, rất tốn bộ nhớ và tính toán. PEFT đóng băng gần như toàn bộ mô hình gốc, chỉ huấn luyện một lượng tham số nhỏ. Ba nhóm phổ biến là reparameterization như LoRA/QLoRA, adapter, và prefix/prompt tuning. Nhờ vậy chi phí huấn luyện và lưu trữ giảm mạnh.

**Nhấn:** PEFT không miễn phí hoàn toàn: mỗi task mới vẫn cần dữ liệu và một quá trình huấn luyện.

**Chuyển:** “Mỗi hướng có điểm nghẽn riêng; ta điểm qua để thấy GEPA và T2L giải quyết gì.”

### Trang 12 — Hạn chế của prompt thủ công · 55–65 giây

**Lời nói:** Với ICL thủ công, chất lượng phụ thuộc vào kinh nghiệm thử-sai, cách diễn đạt và thứ tự ví dụ. Người làm khó biết nên chọn ví dụ nào. Với hệ thống nhiều module, số tổ hợp prompt tăng nhanh đến mức chỉnh tay gần như không khả thi. Đây là động lực để tự động hóa.

**Nhấn:** Vấn đề không phải “không biết viết prompt”, mà là không thể thử hết không gian tổ hợp.

**Chuyển:** “Tự động hóa giải quyết việc thử tay, nhưng lại mở ra hai bài toán chi phí.”

### Trang 13 — Hạn chế của tối ưu prompt tự động · 60 giây

**Lời nói:** Tối ưu tự động cần nhiều rollout để tìm được prompt tốt, nên tốn rollout budget. Đồng thời, nhiều phương pháp có xu hướng nhồi thêm ví dụ few-shot để tăng điểm, làm prompt ngày càng dài và tăng inference token budget. GEPA được thiết kế để tấn công đúng hai chi phí này: dùng phản hồi ngôn ngữ để học nhanh hơn và giữ prompt cô đọng.

**Nhấn:** Hai chi phí: **số lần chạy để tìm** và **độ dài prompt khi triển khai**.

**Chuyển:** “PEFT giải quyết chi phí huấn luyện, nhưng vẫn có nút thắt riêng.”

### Trang 14 — Hạn chế của PEFT · 60 giây

**Lời nói:** PEFT giảm VRAM so với full fine-tuning và giữ inference rẻ, nhưng bản chất vẫn là huấn luyện chuyên biệt cho từng task. Mỗi task mới cần dữ liệu và thời gian train lại. Khác với prompting có thể chuyển task ngay bằng mô tả, PEFT truyền thống không phản ứng tức thời khi chưa có dữ liệu.

**Nhấn:** Nút thắt của PEFT là **chi phí thích nghi lặp lại**, không phải chi phí suy luận.

**Chuyển:** “Vậy có cách nào sinh trọng số ngay từ mô tả mà không cần train lại?”

### Trang 15 — Câu hỏi dẫn sang Text-to-LoRA · 60 giây

**Lời nói:** Câu hỏi chuyển chương là: làm sao giữ ưu điểm cập nhật trọng số và suy luận nhanh của LoRA, nhưng bỏ chi phí dữ liệu và huấn luyện lại cho từng task? Text-to-LoRA trả lời bằng một hypernetwork: nhận mô tả task bằng ngôn ngữ tự nhiên và sinh trực tiếp ma trận LoRA trong một lượt chạy xuôi.

**Nhấn:** Đây là thay đổi từ “train adapter” sang “sinh adapter”.

**Chuyển:** “Nhưng trước khi sang T2L, ta xem GEPA giải quyết bài toán prompt như thế nào.”

---

# Chương 2 — GEPA

### Trang 16 — Divider chương 2 · 15 giây

**Lời nói:** Chương 2 trình bày GEPA, một phương pháp tối ưu prompt bằng tiến hóa có phản chiếu. Trọng số mô hình được đóng băng; GEPA chỉ tối ưu văn bản nhưng dùng phản hồi lỗi chi tiết thay vì chỉ điểm số.

**Chuyển:** “Ta bắt đầu từ bài toán GEPA muốn giải.”

### Trang 17 — Compound AI System · 45 giây

**Lời nói:** Nhắc lại compound AI system gồm nhiều module nối tiếp. Mỗi module có prompt riêng; mục tiêu là tối ưu cả bộ prompt để chất lượng cuối cùng tốt nhất. Vì không thể cập nhật trọng số của các API đóng, GEPA chỉ dịch chuyển trong không gian văn bản.

**Nhấn:** Đầu ra cuối là hàm của cả bộ prompt, không phải một prompt đơn lẻ.

**Chuyển:** “Ta formal hóa bộ prompt đó.”

### Trang 18 — Formal hóa bài toán · 60 giây

**Lời nói:** Hệ thống có k module LLM nối tiếp. Module i được điều khiển bởi prompt π_i. Một ứng viên của hệ thống là tập Φ = {π₁, …, π_k}. Trọng số θ bị đóng băng hoàn toàn, nên bài toán tối ưu là tìm Φ trong không gian văn bản rời rạc. Đây là lý do GEPA có thể áp dụng cho cả mô hình mở và API đóng.

**Nhấn:** Tối ưu rời rạc, không gradient.

**Chuyển:** “Hai công trình gần nhất là MIPROv2 và EvoPrompt.”

### Trang 19 — MIPROv2 · 40–50 giây

**Lời nói:** MIPROv2 là baseline mạnh cho tối ưu prompt trong compound AI system, dùng Bayesian optimization. Nó đóng băng trọng số và tìm tổ hợp instruction và few-shot cho từng module. Vì vậy đây là đối thủ trực tiếp và công bằng nhất của GEPA.

**Nhấn:** MIPROv2 mạnh, nên GEPA vượt được nó mới đáng chú ý.

**Chuyển:** “Cơ chế của MIPROv2 gồm ba bước.”

### Trang 20 — Cơ chế MIPROv2 · 70–80 giây

**Lời nói:** Đầu tiên, bootstrapping chạy hệ thống trên dữ liệu mẫu để thu các cặp few-shot thành công. Tiếp theo, grounded proposal dùng LLM sinh nhiều instruction dựa trên mô tả task và dữ liệu. Cuối cùng, Bayesian optimization đánh giá các tổ hợp instruction và few-shot trên validation để chọn tổ hợp tốt nhất cho từng module. Nó là một quy trình rất có kỷ luật, nhưng tiêu thụ chủ yếu điểm số tổng.

**Nhấn:** Tìm kiếm tổ hợp dựa trên scalar score.

**Chuyển:** “Chính scalar score là điểm yếu khi gặp lỗi phức tạp.”

### Trang 21 — Hạn chế MIPROv2 · 45 giây

**Lời nói:** Vì chỉ dùng điểm tổng, MIPROv2 bỏ phí execution traces: nó biết điểm thấp nhưng không khai thác việc mô hình sai ở bước nào. Nó cũng có xu hướng nhồi thêm few-shot để kéo điểm, khiến prompt dài và tăng chi phí suy luận. GEPA sẽ dùng traces làm tín hiệu học.

**Nhấn:** Mất thông tin chẩn đoán là mất cơ hội sửa đúng chỗ.

**Chuyển:** “EvoPrompt tiếp cận theo hướng tiến hóa, gần với GEPA hơn.”

### Trang 22 — EvoPrompt · 45 giây

**Lời nói:** EvoPrompt kết hợp thuật toán tiến hóa với LLM. Nó duy trì một quần thể prompt, chọn các cá thể điểm cao, rồi dùng LLM để đột biến và lai ghép sinh prompt mới. Đây là tiền đề cho khung tiến hóa của GEPA.

**Nhấn:** Có quần thể và có tiến hóa, nhưng tín hiệu đột biến còn nghèo.

**Chuyển:** “Ba hạn chế của EvoPrompt dẫn trực tiếp tới ba nâng cấp của GEPA.”

### Trang 23 — Hạn chế EvoPrompt · 60 giây

**Lời nói:** Đột biến của EvoPrompt gần như “mù”: nó sửa câu chữ dựa trên điểm số nhưng không biết prompt sai ở bước nào. Chọn lọc theo điểm trung bình dễ làm mất đa dạng và kẹt ở cực trị địa phương. Nó cũng khó mở rộng cho hệ nhiều module. GEPA thay ba điểm này bằng đột biến phản chiếu, biên Pareto và merge theo cấu trúc.

**Nhấn:** Ba nâng cấp tương ứng ba hạn chế.

**Chuyển:** “Trước khi vào thuật toán, GEPA chia dữ liệu thành hai vai trò.”

### Trang 24 — Thiết lập dữ liệu GEPA · 60 giây

**Lời nói:** GEPA tách dữ liệu train thành hai phần. D_feedback dùng để bốc minibatch, chạy thử và lấy lỗi cho reflection. D_pareto là tập cố định dùng như validation nội bộ để chấm và lọc ứng viên. Minibatch thường 3–5 mẫu, đủ ngắn để đọc kỹ lỗi nhưng vẫn đủ nhanh.

**Nhấn:** Tách “học từ lỗi” khỏi “chấm điểm công bằng”.

**Chuyển:** “Bốn khái niệm còn lại cần nắm là P₀, pool, rollout và budget.”

### Trang 25 — Khái niệm cốt lõi · 70–80 giây

**Lời nói:** P₀ là bộ prompt khởi tạo, chỉ cần chạy được chứ chưa cần tối ưu. Candidate pool là cây tiến hóa lưu các ứng viên, điểm trên D_pareto và quan hệ cha-con. Một rollout là một lượt chạy hoàn chỉnh hệ thống trên một mẫu. Rollout budget B giới hạn tổng số lượt chạy; khi hết ngân sách, GEPA chọn ứng viên có điểm trung bình cao nhất trên D_pareto.

**Nhấn:** Budget là tài nguyên trung tâm; mọi cơ chế lọc đều để tiêu budget hiệu quả.

**Chuyển:** “Sơ đồ tổng quát sẽ nối các khái niệm này lại.”

### Trang 26 — Sơ đồ GEPA · 40–50 giây

**Lời nói:** Sơ đồ đi từ P₀, bốc minibatch, chạy hệ thống, đọc traces và phản hồi lỗi, gọi reflection LM để tạo prompt mới, lọc nhanh trên minibatch, rồi mới chấm trên D_pareto và đưa vào pool. Vòng lặp chạy đến khi hết budget. Điểm quan trọng là có hai tầng đánh giá để không lãng phí rollout.

**Nhấn:** Đọc từ trái sang phải; mọi mũi tên quay lại đều là một vòng tiến hóa.

**Chuyển:** “Đây là cùng pipeline trong hình của paper.”

### Trang 27 — Pipeline trong paper · 55–65 giây

**Lời nói:** Hình paper cho thấy GEPA không chỉ sinh prompt mới mà còn duy trì biên Pareto và merge các nhánh. Các khối “select”, “execute”, “reflect”, “evaluate” tương ứng đúng vòng lặp vừa nói. Nhóm em giữ hình gốc để khi cần đối chiếu thuật toán với paper.

**Nhấn:** Không cần đọc từng chữ trong hình; chỉ ra ba khối select–reflect–evaluate.

**Chuyển:** “Đi sâu vào cơ chế chọn lọc đầu tiên: Pareto.”

### Trang 28 — Chọn trên biên Pareto · 70–80 giây

**Lời nói:** Cách tham lam chỉ giữ ứng viên điểm trung bình cao nhất, dễ mất đa dạng vì một ứng viên giỏi nhiều mẫu dễ thống trị. GEPA tính với từng mẫu x_j điểm cao nhất mà quần thể đạt được, gọi là s*(x_j). Ứng viên chỉ bị loại nếu không đạt đỉnh trên bất kỳ mẫu nào. Xác suất chọn tỷ lệ với số mẫu mà ứng viên đó đứng đầu.

**Nhấn:** “Tốt trên ít nhất một mẫu” quan trọng hơn “tốt trung bình”.

**Chuyển:** “Hình sau minh họa việc lọc này.”

### Trang 29 — Minh họa Pareto · 30 giây

**Lời nói:** Các điểm nằm trên biên là những ứng viên không bị thống trị hoàn toàn: không có ứng viên khác tốt hơn ở mọi mẫu. Những điểm nằm trong vùng bị thống trị sẽ bị loại. Nhờ vậy quần thể giữ được nhiều chiến lược khác nhau thay vì co về một prompt duy nhất.

**Nhấn:** Biên Pareto = tập các “chuyên gia” khác nhau.

**Chuyển:** “Điều này đánh đổi thế nào giữa khai thác và khám phá?”

### Trang 30 — Ý nghĩa Pareto · 45 giây

**Lời nói:** Giữ nhiều ứng viên giúp cân bằng khai thác và khám phá. Ứng viên giỏi nhiều mẫu được chọn thường xuyên để khai thác; ứng viên chỉ giỏi một nhóm mẫu khó vẫn có cơ hội được chọn để khám phá hướng mới. Đây là cơ chế chống overfit vào một vài mẫu.

**Nhấn:** Đa dạng chiến lược có chủ đích, không phải nhiễu.

**Chuyển:** “Cơ chế thứ hai là đột biến bằng phản chiếu.”

### Trang 31 — Reflective Prompt Mutation · 25–30 giây

**Lời nói:** Đột biến phản chiếu không sửa ngẫu nhiên. Reflection LM đọc prompt hiện tại, execution traces và phản hồi lỗi để chẩn đoán nguyên nhân, rồi viết lại prompt nhằm sửa đúng lỗi đó.

**Nhấn:** Tín hiệu học là văn bản chẩn đoán, không phải chỉ con số.

**Chuyển:** “Quy trình gồm bốn bước.”

### Trang 32 — Cơ chế reflective mutation · 85–95 giây

**Lời nói:** GEPA chọn module theo round-robin, chạy ứng viên trên minibatch để lấy traces và phản hồi lỗi. Reflection LM nhận prompt cũ, traces và feedback để viết prompt mới cô đọng hơn. Sau đó có màng lọc hai tầng: nếu điểm trên chính minibatch không tăng thì loại ngay; nếu tăng mới chấm trên D_pareto và thêm vào pool. Cách này tiết kiệm budget vì không lãng phí đánh giá đắt cho ứng viên rõ ràng kém.

**Nhấn:** Hai tầng lọc: minibatch rẻ trước, D_pareto đắt sau.

**Chuyển:** “Khi có nhiều nhánh tốt, GEPA ghép chúng bằng LCA.”

### Trang 33 — System-aware Merge · 70–80 giây

**Lời nói:** Merge được kích hoạt sau một đột biến thành công nếu trên biên có ít nhất hai ứng viên thuộc các nhánh khác nhau chưa ghép. GEPA tìm tổ tiên chung gần nhất, so từng module và lấy phiên bản đã được cải thiện ở mỗi nhánh. Nếu cả hai cùng sửa một module, ưu tiên nhánh điểm cao hơn. Bản ghép được thử nhanh trên minibatch trước khi chấm D_pareto.

**Nhấn:** Merge không tốn reflection call; nó tái tổ hợp các cải tiến đã có.

**Chuyển:** “Hình 9 minh họa cách các nhánh hội tụ.”

### Trang 34 — Minh họa merge · 30 giây

**Lời nói:** Hình cho thấy hai nhánh cùng xuất phát từ một tổ tiên, mỗi nhánh sửa các module khác nhau. Bản merge kế thừa phần tốt của cả hai thay vì chọn một nhánh và bỏ phần còn lại. Đây là điểm khác biệt so với lai ghép prompt đơn lẻ.

**Nhấn:** Ghép theo module và theo cây, không trộn câu chữ tùy ý.

**Chuyển:** “Phần thực nghiệm kiểm tra các cơ chế này trên bốn benchmark.”

### Trang 35 — Thiết lập thực nghiệm GEPA · 60 giây

**Lời nói:** Paper đánh giá trên Qwen3 8B mã nguồn mở và GPT-4.1 mini qua API. Bốn benchmark là HotpotQA cho hỏi đáp đa bước, IFBench cho tuân thủ chỉ dẫn, HoVer cho kiểm chứng thông tin và PUPA cho ủy quyền bảo mật quyền riêng tư. Baseline gồm P₀, GRPO cho RL, MIPROv2 cho prompt optimization, và hai cấu hình GEPA/GEPA+Merge.

**Nhấn:** Cùng lúc so với RL và prompt optimization, trên cả mô hình mở lẫn đóng.

**Chuyển:** “Kết quả đầu tiên là so với GRPO.”

### Trang 36 — Vượt GRPO với ít rollout hơn · 60 giây

**Lời nói:** Trên Qwen3 8B, GEPA vượt GRPO trên cả bốn benchmark, trung bình khoảng 10% và có task tới khoảng 20%. Điều đáng chú ý là hiệu quả mẫu: GRPO cần tới khoảng 24.000 rollouts, trong khi GEPA chỉ cần vài trăm đến khoảng 1.200, tiết kiệm tới 35 lần. Lý do là GEPA học từ phản hồi ngôn ngữ giàu thông tin thay vì chỉ phần thưởng vô hướng.

**Nhấn:** Hai con số phải nhớ: **~10%** và **35× ít rollout hơn**.

**Chuyển:** “So với prompt optimizer mạnh nhất thì sao?”

### Trang 37 — Vượt MIPROv2 · 60 giây

**Lời nói:** GEPA vượt MIPROv2 trên tất cả benchmark ở cả Qwen3 8B và GPT-4.1 mini, trung bình hơn 10%. Kết quả này cho thấy đột biến phản chiếu cộng biên Pareto hiệu quả hơn tìm kiếm tổ hợp Bayesian chỉ dựa trên điểm tổng. Nó cũng ổn định khi mô hình là API đóng, tức khi không thể cập nhật trọng số.

**Nhấn:** Thắng trên cả mô hình mở và đóng mới là điểm mạnh.

**Chuyển:** “Không chỉ điểm cao hơn, prompt còn ngắn hơn.”

### Trang 38 — Prompt ngắn hơn · 45 giây

**Lời nói:** MIPROv2 có xu hướng nhồi few-shot để kéo điểm, nên prompt rất dài. GEPA tổng hợp lỗi thành các quy tắc cô đọng, nhờ đó prompt ngắn hơn tới 9 lần. Điều này giảm inference token budget và độ trễ khi triển khai thực tế.

**Nhấn:** Chất lượng tăng nhưng chi phí suy luận giảm.

**Chuyển:** “Còn hai thành phần Pareto và Merge đóng góp bao nhiêu?”

### Trang 39 — Ablation Pareto và Merge · 55–65 giây

**Lời nói:** Chọn Pareto luôn tốt hơn tham lam vì giữ đa dạng chiến lược và tránh kẹt cực trị địa phương. Với merge, trên GPT-4.1 mini, GEPA+Merge tăng thêm khoảng 5% so với GEPA thường. Trên Qwen3 8B, merge nhạy cảm với thời điểm: ghép quá sớm có thể làm điểm trung bình giảm nhẹ.

**Nhấn:** Merge có lợi nhưng không miễn phí; thời điểm ghép quan trọng.

**Chuyển:** “Vậy giới hạn của GEPA là gì?”

### Trang 40 — Giới hạn của GEPA · 60 giây

**Lời nói:** GEPA phụ thuộc vào reflection LM và chất lượng phản hồi. Nếu bài toán chỉ có điểm số thô, không có traces hoặc mô tả lỗi rõ ràng, reflection khó chẩn đoán đúng. Merge nhạy cảm với năng lực mô hình và thời điểm. Cuối cùng, vì trọng số bị đóng băng, GEPA không thể nạp kiến thức chuyên ngành hoàn toàn mới hay vượt trần suy luận của mô hình gốc.

**Nhấn:** Trần của GEPA là trần của mô hình gốc.

**Chuyển:** “Ba điểm cần nhớ về GEPA.”

### Trang 41 — Tổng kết GEPA · 45 giây

**Lời nói:** Thứ nhất, phản hồi ngôn ngữ giàu thông tin hơn điểm thưởng vô hướng, giúp GEPA vượt GRPO với ít rollout hơn tới 35 lần. Thứ hai, Pareto và merge giúp tối ưu hệ nhiều module. Thứ ba, prompt ngắn hơn tới 9 lần nên giảm chi phí triển khai. Nhưng khi prompt chạm trần, ta phải quay lại thích nghi trọng số — đó là lý do sang Text-to-LoRA.

**Nhấn:** GEPA tối ưu cách hỏi, không thêm năng lực vào trọng số.

**Chuyển:** “Chương 3 giải quyết đúng phần trần đó.”

---

# Chương 3 — Text-to-LoRA

### Trang 42 — Divider chương 3 · 10–15 giây

**Lời nói:** Text-to-LoRA, công bố ở ICML 2025, đặt câu hỏi: có thể sinh adapter LoRA trực tiếp từ mô tả task mà không cần huấn luyện lại không?

**Chuyển:** “Bắt đầu từ tình huống rất thực tế.”

### Trang 43 — Tình huống task mới · 40–45 giây

**Lời nói:** Khi có một task mới, cách quen thuộc là fine-tune LoRA. Nhưng nếu đã từng giải quyết vài task gần giống, liệu có thể tận dụng chúng thay vì bắt đầu lại? Đây là câu hỏi dẫn tới ba hướng tiếp cận ở trang sau.

**Nhấn:** Tận dụng tri thức cũ nhưng vẫn thích nghi cho task mới.

**Chuyển:** “Ba cách hiện có đều có điểm nghẽn.”

### Trang 44 — Ba cách hiện có và hạn chế · 70–80 giây

**Lời nói:** Cách một là nén nhiều task bằng SVD vào một ma trận chung; tiết kiệm bộ nhớ nhưng mất hiệu năng. Cách hai là chọn một tập task cũ gần giống; bị giới hạn bởi những gì đã có. Cách ba là dùng hypernetwork sinh adapter, nhưng các phương pháp cũ thường nhận task ID cố định hoặc câu hỏi từ task mới, vẫn phụ thuộc task cũ, tốn thời gian train và người dùng không kiểm soát được.

**Nhấn:** Thiếu một giao diện tự nhiên để người dùng mô tả task mới.

**Chuyển:** “T2L thay input của hypernetwork bằng mô tả ngôn ngữ tự nhiên.”

### Trang 45 — Ý tưởng T2L · 40–45 giây

**Lời nói:** Mục tiêu là một mô hình có thể sinh adapter từ mô tả của người dùng. Người dùng viết task cần làm; hypernetwork biến mô tả đó thành trọng số LoRA; mô hình gốc đóng băng và dùng adapter để trả lời. Không cần tập train cho task mới.

**Nhấn:** Mô tả là giao diện, adapter là đầu ra.

**Chuyển:** “Để hiểu cách sinh, cần nhắc lại hypernetwork.”

### Trang 46 — Hypernetwork · 40–45 giây

**Lời nói:** Hypernetwork là một mạng sinh ra trọng số cho một mạng khác. Thay vì tự học trực tiếp tham số của mô hình đích, nó học ánh xạ từ một điều kiện đầu vào sang bộ tham số. Trong T2L, điều kiện đầu vào là mô tả task.

**Nhấn:** “Mạng sinh trọng số cho mạng khác.”

**Chuyển:** “Với mô hình lớn, sinh toàn bộ trọng số là quá đắt, nên người ta sinh adapter.”

### Trang 47 — Hypernetwork sinh adapter · 30 giây

**Lời nói:** Thay vì sinh toàn bộ weight, hypernetwork chỉ sinh các ma trận adapter. Số tham số cần sinh giảm rất mạnh, trong khi mô hình gốc vẫn đóng băng. Đây là cầu nối giữa ý tưởng hypernetwork và PEFT.

**Nhấn:** Sinh phần nhỏ, không sinh cả mô hình.

**Chuyển:** “T2L cụ thể hóa ý tưởng này như sau.”

### Trang 48 — Luồng T2L · 55–60 giây

**Lời nói:** Với một task mới, T2L lấy mô tả task, thường do GPT-4 mini viết, đưa qua text encoder và hypernetwork để sinh các ma trận adapter. Các adapter này được gắn vào mô hình ngôn ngữ đóng băng để thực hiện task. Toàn bộ quá trình thích nghi chỉ là một lượt forward, không có gradient descent trên task mới.

**Nhấn:** Train một lần cho hypernetwork; dùng mãi cho nhiều task.

**Chuyển:** “Kiến trúc có bốn module; module 1 là ánh xạ mô tả sang trọng số.”

### Trang 49 — Module 1: công thức · 55–60 giây

**Lời nói:** Công thức là W = g(f(z)): z là mô tả task, f là text encoder, g là hypernetwork, W là ma trận cần sinh. Nếu để W kích thước N×N ở đầu ra, lớp fully-connected cuối sẽ có số tham số khổng lồ. Vì vậy T2L phân rã W thành cặp ma trận A và B, giống tinh thần LoRA.

**Nhấn:** Phân rã bậc thấp để giảm số tham số.

**Chuyển:** “Nhưng chỉ một cặp A, B vẫn chưa đủ cho toàn mô hình.”

### Trang 50 — Module 1: quá nhiều cặp · 70–80 giây

**Lời nói:** Mistral-7B có 32 lớp transformer; nếu mỗi lớp cần hai cặp cho q và v thì cần khoảng 64 cặp A, B. Nếu lớp hidden cuối của hypernetwork là 512, lớp FC sinh đủ 64 cặp sẽ có khoảng 1,7 tỷ tham số, quá lớn. T2L giải quyết bằng cách thêm hai tín hiệu đầu vào: đây là layer thứ mấy và đây là module key hay value.

**Nhấn:** 32 lớp × 2 module = 64 cặp; bài toán là đầu ra quá lớn.

**Chuyển:** “Cách thêm layer và module key được viết gọn trong một công thức.”

### Trang 51 — Module 1: concat layer/module · 55–60 giây

**Lời nói:** Công thức mới là ΔW = h_θ(concat[f(z), E[m], E[l]]), trong đó E[m] là embedding của module key và E[l] là embedding của layer. Nhờ vậy cùng một hypernetwork sinh được adapter cho từng vị trí. Số tham số giảm còn khoảng 55 triệu. Vì hypernetwork chạy rất nhanh, có thể chạy theo batch để sinh đủ 64 cặp.

**Nhấn:** Từ 1,7 tỷ xuống khoảng **55M**.

**Chuyển:** “Vậy nên chọn đầu ra là cả cặp, một ma trận, hay một hàng?”

### Trang 52 — Module 1: chọn dạng đầu ra · 30–35 giây

**Lời nói:** Sau khi đã giảm được số tham số, câu hỏi tiếp theo là nên sinh cả cặp (A, B), sinh từng ma trận A hoặc B, hay sinh từng hàng. Sinh càng nhỏ thì batch càng lớn và số tham số càng ít, nhưng yêu cầu thêm tín hiệu để hypernetwork biết đang sinh phần nào. Ba lựa chọn này dẫn tới ba biến thể L, M, S ở trang sau.

**Nhấn:** Đây là đánh đổi giữa biểu diễn đầy đủ và kích thước mô hình.

**Chuyển:** “Bảng sau tóm tắt ba cấu hình L/M/S.”

### Trang 53 — Ba biến thể L/M/S · 40–45 giây

**Lời nói:** L sinh cả A và B, batch 64, khoảng 55M tham số. M sinh A hoặc B, thêm tín hiệu A/B, batch 128, khoảng 34M. S sinh từng hàng, thêm tín hiệu A/B và chỉ số hàng, batch 1024, chỉ khoảng 5M. Kết quả chất lượng của ba biến thể được để ở cuối chương.

**Nhấn:** L lớn nhất, S nhỏ nhất; chưa kết luận biến thể nào tốt nhất ở trang này.

**Chuyển:** “Module 2 kiểm tra mô tả task có thực sự tạo khác biệt không.”

### Trang 54 — Module 2: ví dụ toán · 55–65 giây

**Lời nói:** Bài toán có Seattle 20 con cừu, Charleston gấp 4 lần Seattle nên 80, Toulouse gấp đôi Charleston nên 160; tổng là 260. Baseline trên slide trả 240, sai ở bước suy luận quan hệ. Ví dụ này cho thấy lỗi không chỉ là thiếu kiến thức mà có thể là cách mô hình diễn giải quan hệ.

**Nhấn:** Đáp án đúng là **260**, không phải 240.

**Chuyển:** “Nếu thay mô tả task, adapter có sửa được kiểu lỗi này không?”

### Trang 55 — Module 2: chất lượng mô tả · 40 giây

**Lời nói:** Slide so ba kiểu mô tả: mô tả kém, mô tả theo hướng toán học và theo hướng lập trình. Kết quả định tính cho thấy cùng một task nhưng cách mô tả khác nhau tạo adapter khác nhau và chất lượng trả lời khác nhau. Vì vậy mô tả là một phần của phương pháp, không phải chi tiết phụ.

**Nhấn:** Chất lượng đầu vào văn bản quyết định chất lượng adapter.

**Chuyển:** “Module 3 nói về text encoder.”

### Trang 56 — Module 3: text encoder · 55–60 giây

**Lời nói:** T2L dùng gte-large-en làm text encoder thay vì encoder của mô hình ngôn ngữ. Tác giả lập luận rằng encoder độc lập giúp biểu diễn mô tả tốt hơn; các phương pháp như HINT hay HyperTune cũng cho thấy dùng text encoder ngoài có ích. Cách này cũng tách việc hiểu mô tả khỏi mô hình đích.

**Nhấn:** Encoder ngoài, không dùng tokenizer/encoder của LM đích.

**Chuyển:** “Vì sao lại chọn đúng gte-large-en?”

### Trang 57 — Vì sao chọn gte-large-en · 30 giây

**Lời nói:** Tại thời điểm paper ra đời, gte-large-en có hiệu năng rất mạnh cho embedding văn bản và kích thước tương đối nhẹ, khoảng 400 triệu tham số. Đây là lựa chọn thực dụng giữa chất lượng biểu diễn và chi phí.

**Nhấn:** Không phải lựa chọn duy nhất, mà là cân bằng tốt ở thời điểm đó.

**Chuyển:** “Module 4 là cách huấn luyện hypernetwork.”

### Trang 58 — Huấn luyện bằng Reconstruction · 55–60 giây

**Lời nói:** Cách reconstruction huấn luyện trước một LoRA riêng cho từng task, sau đó cho hypernetwork sinh adapter và dùng MSE giữa adapter sinh ra với adapter đã train để cập nhật hypernetwork. Cách này có ground truth rõ ràng nhưng tốn công train adapter cho mọi task.

**Nhấn:** Học bắt chước adapter có sẵn.

**Chuyển:** “Cách thứ hai bỏ trung gian adapter chuẩn và học trực tiếp từ đầu ra.”

### Trang 59 — Huấn luyện bằng SFT · 60 giây

**Lời nói:** Với SFT, hypernetwork sinh adapter, gắn adapter vào mô hình ngôn ngữ đóng băng, cho mô hình trả lời câu hỏi, rồi dùng cross-entropy giữa câu trả lời và đáp án để cập nhật hypernetwork. Ở đây hypernetwork được tối ưu trực tiếp cho việc trả lời đúng, không phải cho việc tái tạo một ma trận.

**Nhấn:** Loss cuối cùng là loss của task, không phải loss của weight.

**Chuyển:** “So sánh hai cách này cho thấy SFT tốt hơn.”

### Trang 60 — Reconstruction vs SFT · 70–80 giây

**Lời nói:** Kết quả cho thấy SFT hiệu quả hơn reconstruction. Có hai lý do. Thứ nhất, nghiệm tối ưu của bài toán adapter không đồng nhất: nhiều bộ trọng số khác nhau có thể cho cùng chất lượng. Thứ hai, MSE đo khoảng cách ma trận chứ không đo mô hình trả lời tốt hay kém. Vì vậy tối ưu trực tiếp bằng CE sát mục tiêu hơn.

**Nhấn:** Weight giống chưa chắc hành vi giống; hãy tối ưu hành vi.

**Chuyển:** “Ba bảng thực nghiệm kiểm tra chất lượng và chi phí.”

### Trang 61 — So với LoRA · 55–65 giây

**Lời nói:** Bảng này so T2L với LoRA trên các task. Điểm cần nói không phải từng ô số, mà là T2L tiến gần chất lượng LoRA huấn luyện chuyên biệt trong khi không cần train trên task mới. Đây là đánh đổi có chủ đích: chấp nhận kém hơn một chút để đổi lấy tốc độ thích nghi.

**Nhấn:** So sánh là “gần bằng với chi phí gần như bằng 0”, không phải “vượt LoRA”.

**Chuyển:** “So với các phương pháp thích nghi khác thì sao?”

### Trang 62 — So với các phương pháp khác · 45 giây

**Lời nói:** Bảng tiếp theo đặt T2L cạnh các baseline thích nghi khác. Cách đọc là so theo cùng nhóm task và cùng mô hình, không so tuyệt đối giữa các cột khác thiết lập. T2L nằm trong nhóm cạnh tranh và giữ lợi thế lớn về thời gian sinh adapter.

**Nhấn:** Chỉ so trong cùng điều kiện thực nghiệm.

**Chuyển:** “Ba biến thể L/M/S đánh đổi cụ thể ra sao?”

### Trang 63 — Kết quả L/M/S · 45 giây

**Lời nói:** Bảng cho thấy biến thể L thường cho chất lượng tốt nhất nhưng nhiều tham số nhất. M và S giảm mạnh kích thước, đổi lại chất lượng giảm. Đây là lựa chọn triển khai: nếu ưu tiên độ chính xác dùng L; nếu ưu tiên bộ nhớ hoặc nhiều adapter song song, có thể dùng M hoặc S. Nhóm không tuyên bố S ngang L, chỉ nói S tiết kiệm hơn.

**Nhấn:** Không có biến thể tốt nhất cho mọi ràng buộc.

**Chuyển:** “Trang tiếp theo tổng kết chi phí và hạn chế của toàn chương.”

### Trang 64 — Chi phí và hạn chế · 45–55 giây

**Lời nói:** T2L cần khoảng 0,86 TFLOPs mỗi câu, so với 4,18 TFLOPs của 3-shot ICL, tức rẻ hơn khoảng 5 lần. Hạn chế là phụ thuộc chất lượng mô tả; trong paper mô tả do GPT-4o-mini viết. Nhóm chưa kiểm tra chuyển từ mô hình nhỏ sang mô hình lớn, nên không nên nói T2L là zero-shot vạn năng.

**Nhấn:** Rẻ hơn ~5×, nhưng mô tả là điểm yếu và transfer giữa model chưa được chứng minh.

**Chuyển:** “Đó là hai hướng riêng; chương 4 kiểm tra chúng trên cùng một harness.”

---

# Chương 4 — Thực nghiệm, kết hợp và demo

### Trang 65 — Divider chương 4 · 15 giây

**Lời nói:** Chương 4 là phần nhóm tự chạy. Mục tiêu là kiểm tra T2L mạnh đến đâu, GEPA thêm được gì, và ghép hai phương pháp có tạo synergy thật không. Nhóm dùng Mistral-7B-Instruct-v0.2, năm benchmark, mỗi task 1.000 câu test.

**Nhấn:** Khoảng 20–22 phút số liệu, 8–10 phút demo.

**Chuyển:** “Bắt đầu bằng thiết lập chung.”

### Trang 66 — Thiết lập thí nghiệm · 60–70 giây

**Lời nói:** Mọi phương pháp dùng cùng Mistral-7B-Instruct-v0.2 và cùng năm task lấy từ T2L, mỗi task 1.000 câu test. Base zero-shot và ICL3 là hai control. T2L thay trọng số bằng LoRA `r=8` và được đo ở cả 0-shot lẫn ICL3. GEPA giữ base, tìm instruction và giữ ba demonstrations. T2L + GEPA tìm instruction khi adapter đang trả lời.

**Nhấn:** Cùng model và cùng bộ test; điểm khác nhau nằm ở bề mặt thích nghi.

**Chuyển:** “Trước khi đọc kết quả, bảng này đặt số của paper cạnh số nhóm chạy lại.”

### Trang 67 — So sánh kết quả Paper và nhóm · 100–110 giây

**Lời nói:** Bảng giữ accuracy thô, không quy về chênh lệch. Với T2L 0-shot, paper có 45,8 GSM8K; 77,5 ARC-C; 85,0 BoolQ; 66,5 HellaSwag; 64,2 WinoGrande. Nhóm đo được 39,1; 70,7; 85,1; 61,7 và 28,1. HellaSwag sát paper nhất, 61,7 so với 66,5. WinoGrande zero-shot chỉ 28,1 vì adapter trả sai format; khi thêm ba demonstrations lên 64,2. Cột T2L+ICL3 là cấu hình bổ sung, không cùng thiết lập paper. Base nhóm cao hơn paper trên ba task do harness, prompt và extractor khác; không nên nói mô hình nhóm mạnh hơn.

**Nhấn:** Paper dùng 3 adapters/task, nhóm dùng 1; chỉ đối chiếu xu hướng, không so tuyệt đối.

**Chuyển:** “Trong cùng harness của nhóm, T2L+ICL3 cải thiện những task nào có ý nghĩa?”

### Trang 68 — T2L tạo cải thiện có ý nghĩa trên 3/5 task · 100–110 giây

**Lời nói:** So T2L+ICL3 với base, BoolQ tăng 3,3 điểm, HellaSwag tăng 16,0 và WinoGrande tăng 4,8; cả ba CI không chứa 0. GSM8K tăng 0,6 và ARC-C giảm 0,5 nhưng CI chứa 0, nên chưa kết luận. T2L có điểm quan sát cao nhất trên 4/5 task, nhưng chỉ 3/5 task có cải thiện có ý nghĩa thống kê. Mean +4,8 là trung bình năm task, không phải mức tăng đồng đều.

**Nhấn:** Phân biệt “cao nhất trên 4/5” và “có ý nghĩa trên 3/5”.

**Chuyển:** “GEPA được so với baseline công bằng nhất: ICL3.”

### Trang 69 — GEPA chưa vượt baseline ICL3 · 100–110 giây

**Lời nói:** GEPA và ICL3 cùng base, cùng ba demonstrations. GEPA đạt 62,6 trung bình, thấp hơn ICL3 0,4 điểm. GEPA giữ nguyên seed ở 4/5 task; task duy nhất instruction thay đổi là ARC-C, nhưng accuracy lại giảm 1,5 điểm. Các task còn lại gần như trùng baseline, nên lợi ích chủ yếu đến từ demonstrations chứ không từ instruction search.

**Nhấn:** 4/5 giữ seed; task duy nhất đổi prompt lại giảm 1,5 điểm.

**Chuyển:** “Chi phí cho thấy cùng một ngân sách search nhưng thời gian khác nhau.”

### Trang 70 — Chi phí · 80–90 giây

**Lời nói:** Bảng so bốn arm trên tổng năm task. Hai arm không search có 0 search call. GEPA trên base và T2L+GEPA có số search call gần như nhau, nhưng final-test token và wall time khác. Adapter trả lời ngắn hơn nên search trên adapter ít tốn token hơn. Khi đọc bảng, nhớ wall time gồm search + final test, còn token chỉ tính final test; token trong search không được meter.

**Nhấn:** So sánh phải tách “chi phí tìm prompt” khỏi “chi phí chạy test”.

**Chuyển:** “Pipeline dưới đây giải thích vì sao T2L+GEPA lại chạy rollout trên adapter.”

### Trang 71 — Pipeline đồng tối ưu · 60–70 giây

**Lời nói:** Adapter được sinh một lần từ mô tả gốc rồi đóng băng. GEPA chỉ sửa instruction. Mọi rollout chạy trên t2l_<task>, reflection đọc lỗi của chính mô hình đã adapt, rồi đề xuất instruction mới. Ngân sách 1.500 metric call mỗi task; instruction tốt nhất mới được chạy greedy trên 1.000 câu test. Điểm khác biệt so với GEPA trên base là nơi rollout chạy, không phải thuật toán.

**Nhấn:** Adapter cố định, instruction thay đổi, reflection thấy failure mode của model đã adapt.

**Chuyển:** “Kết quả của cách ghép này rất khiêm tốn.”

### Trang 72 — Kết quả kết hợp T2L + GEPA · 90–100 giây

**Lời nói:** So T2L+GEPA với T2L+ICL3, trung bình tăng 0,1 điểm. Không task nào có CI loại 0; delta từng task nằm trong khoảng −0,8 đến +0,6. T2L+GEPA giữ nguyên seed ở 2/5 task là GSM8K và WinoGrande. Toàn bộ mức tăng so với base chủ yếu đến từ adapter và demos, không phải từ prompt search. Vì vậy không nên nói đồng tối ưu tạo ra bước nhảy mới.

**Nhấn:** +0,1 pp trung bình; 0/5 task có ý nghĩa; seed giữ nguyên ở 2/5.

**Chuyển:** “Bảng tổng hợp đặt tất cả phiên bản cạnh nhau.”

### Trang 73 — Kết quả đầy đủ · 45–55 giây

**Lời nói:** Bảng giữ sáu phiên bản để tra cứu. Điểm cần nhớ không phải từng ô, mà là T2L+ICL3 và T2L+GEPA gần như trùng nhau; GEPA trên base không vượt 3-shot. T2L zero-shot rất thấp trên WinoGrande vì lỗi format; khi thêm demos mới trở lại bình thường. Các ô in đậm là best theo điểm quan sát, không hàm ý khác biệt có ý nghĩa.

**Nhấn:** T2L làm phần lớn; GEPA thêm rất ít; GEPA trên base không vượt 3-shot.

**Chuyển:** “Cấu hình GEPA tóm tắt những gì đã chạy phía sau.”

### Trang 74 — Cấu hình GEPA · 45–55 giây

**Lời nói:** Mỗi task có ngân sách 1.500 metric call: 300 để chấm tập chọn và 1.200 để tìm kiếm. D_train có 150 câu, D_pareto có 300 câu. Rollout dùng temperature 0,6. Reflection LM là deepseek-v4.1-flash, nhận output, đáp án đúng, đúng/sai và lời giải tham khảo.

**Nhấn:** GEPA chỉ sửa instruction; trọng số và demonstrations không đổi.

**Chuyển:** “Phần cuối là demo trực tiếp.”

### Trang 75 — Demo · 8–10 phút

**Lời nói:** Chạy cùng một câu WinoGrande qua Base, T2L, GEPA và T2L+GEPA; đối chiếu output, đáp án trích được, latency và token. Sau đó mở prompt history để kiểm tra seed, candidates và best. Nếu dịch vụ lỗi, dùng prompt/per-item đã lưu trong artifact bundle; không dựng kết quả giả.

**Fallback:** `docs/demo.md` và `/data/quan.lt/temp/t2l-mistral/artifacts/mistral-7b-v1/`.

**Nhấn:** Demo dùng generation thật, không mô phỏng search.

**Chuyển:** “Nhóm em xin kết thúc và nhận câu hỏi.”

### Trang 76 — Cảm ơn · 20–30 giây

**Lời nói:** Nhóm em xin cảm ơn thầy cô và các bạn. Tóm tắt một câu: T2L tạo phần cải thiện rõ và rẻ; GEPA trên base không vượt 3-shot; đồng tối ưu đúng về thiết kế nhưng lợi ích thêm hiện rất nhỏ và chưa đủ bằng chứng. Nhóm sẵn sàng nhận câu hỏi.

**Chuyển:** Mở Q&A.

---



Dùng các câu trả lời ngắn dưới đây khi bị hỏi; số liệu chi tiết mở bảng tổng hợp
ở trang 73 hoặc report trong `docs/report/mistral-api-v1/`.

1. **Vì sao không so tuyệt đối với paper?**
   Harness của nhóm dễ hơn lm-eval: base Mistral cao hơn paper 8–14 điểm trên ARC-C, BoolQ, WinoGrande. Chỉ delta trong cùng harness mới có nghĩa.

2. **Vì sao headline dùng T2L+ICL3 trong khi paper đo T2L zero-shot?**
   Paper không kèm ICL, nên phần tái lập so đúng zero-shot. T2L+ICL3 là cấu hình ứng dụng bổ sung; trên WinoGrande, 3-shot chỉ sửa format, không phải năng lực mới.

3. **T2L có thực sự thắng 4/5 task không?**
   Có điểm quan sát cao nhất trên 4/5, nhưng chỉ 3/5 có CI không chứa 0: BoolQ, HellaSwag, WinoGrande.

4. **GEPA có tệ hơn 3-shot không?**
   Trong run chuẩn, trung bình GEPA thấp hơn ICL3 0,4 điểm; GEPA giữ seed 4/5 task. Task duy nhất đổi prompt là ARC-C lại giảm 1,5. Vì vậy lợi ích chủ yếu đến từ demonstrations.

5. **Vì sao T2L+GEPA chỉ +0,1 mà vẫn nói là hướng đúng?**
   Đồng tối ưu tránh được kiểu hỏng của prompt transfer, nên đúng về thiết kế. Nhưng bằng chứng hiện tại chưa đủ để nói nó tạo synergy; cần nhiều seed.

6. **Vì sao hai lần chạy lệch 1,3–1,5 điểm?**
   Search chọn prompt khác nhau giữa hai trajectory. Các arm cố định chỉ lệch ≤0,3 điểm, nên nguồn chính là search, không phải cách chấm test.

7. **Sao prompt “tối ưu” lại dài hàng nghìn ký tự?**
   GEPA có thể thêm quy tắc và ví dụ để sửa lỗi. Trong run chuẩn, prompt tăng lên nhưng không tạo gain có ý nghĩa; đây chính là bằng chứng cần thận trọng.

8. **Demo có dùng kết quả thật không?**
   Có. Demo đọc adapter, prompt và per-item generation từ artifact bundle. Không sinh lại search và không mô phỏng kết quả. Khi dịch vụ lỗi, dùng prompt history/per-item đã lưu.
