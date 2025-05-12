# Room Escape - Game Giải Mê Cung Thông Minh

Chào mừng bạn đến với Room Escape, một trò chơi giải mê cung thông minh được phát triển bằng Pygame! Trò chơi này không chỉ cho phép bạn tự mình khám phá và giải các căn phòng mê cung được tạo ngẫu nhiên mà còn cung cấp một nền tảng để so sánh hiệu suất của nhiều thuật toán tìm đường khác nhau.

## Tính Năng Nổi Bật

*   **Tạo Mê Cung Ngẫu Nhiên**: Mỗi lần chơi là một thử thách mới với mê cung được tạo tự động bằng thuật toán Randomized Depth-First Search, có khả năng tạo thêm các vòng lặp để tăng độ phức tạp.
*   **Đa Dạng Vật Phẩm và Chướng Ngại Vật**:
    *   **Chìa khóa (Keys)**: Người chơi/thuật toán cần thu thập đủ số lượng chìa khóa yêu cầu trước khi có thể đến ô đích.
    *   **Bùn (Mud Puddles)**: Làm chậm tốc độ di chuyển của người chơi và tăng chi phí di chuyển cho thuật toán.
    *   **Đường Trượt Nước (Water Slides)**: Khi bước vào, người chơi/thuật toán sẽ tự động trượt theo một hướng cố định đến cuối đường trượt hoặc khi gặp vật cản.
    *   **Cổng Dịch Chuyển (Portals)**: Các cặp cổng dịch chuyển tức thời người chơi/thuật toán giữa hai vị trí trong mê cung.
*   **Điều Khiển Trực Quan**: Giao diện người dùng hiện đại, dễ sử dụng với các nút điều khiển rõ ràng, thanh trượt tốc độ game, và khu vực hiển thị thông tin chi tiết.
*   **Chế Độ Chơi Đa Dạng**:
    *   **Player Mode**: Tự tay điều khiển nhân vật để giải mê cung.
    *   **Algorithm Mode**: Chọn một trong nhiều thuật toán để xem nó tự động tìm đường.
*   **Trực Quan Hóa Thuật Toán**: Theo dõi quá trình "suy nghĩ" của các thuật toán tìm kiếm khi chúng khám phá mê cung, hiển thị các nút đã duyệt, biên giới tìm kiếm và đường đi cuối cùng.
*   **So Sánh Thuật Toán**: Chạy nhiều thuật toán trên cùng một mê cung và xem bảng so sánh chi tiết về:
    *   Khả năng tìm thấy đường đi.
    *   Chi phí của đường đi (đối với thuật toán) / Thời gian hoàn thành (đối với người chơi).
    *   Số bước của đường đi.
    *   Số nút đã duyệt (hiệu quả tính toán).
    *   Tóm tắt các thuật toán tối ưu nhất về chi phí và số bước.
*   **Âm Nhạc và Âm Thanh**: Nhạc nền cho gameplay và menu, cùng với hiệu ứng âm thanh khi nhặt chìa khóa.
*   **Lưu Trữ Kết Quả**: Các báo cáo chi tiết về mỗi lần chạy được tự động lưu vào file `maze_run_reports.txt`.

## Các Thuật Toán Được Sử Dụng

Chương trình này triển khai và cho phép so sánh các thuật toán giải mê cung sau:

### 1. Thuật Toán Tạo Mê Cung

*   **Randomized Depth-First Search (DFS)**: Được sử dụng để tạo cấu trúc cơ bản của mê cung. Thuật toán này hoạt động bằng cách "đục" các đường đi từ một điểm bắt đầu, ưu tiên đi sâu nhất có thể theo một hướng ngẫu nhiên trước khi quay lui. Một tùy chọn cho phép thêm các vòng lặp (loops) vào mê cung sau khi cấu trúc cơ bản đã được hình thành, bằng cách ngẫu nhiên phá bỏ một số bức tường giữa các đường đi hiện có.

### 2. Thuật Toán Giải Mê Cung (Tìm Đường)

Người dùng có thể chọn một trong các thuật toán sau để giải mê cung:

*   **Breadth-First Search (BFS)**:
    *   **Loại**: Tìm kiếm mù (Uninformed Search).
    *   **Đặc điểm**: Duyệt mê cung theo từng lớp kề nhau. Đảm bảo tìm ra đường đi có số bước ngắn nhất (nếu tất cả các bước đi có chi phí như nhau).
    *   **Hiển thị**: Các ô đã duyệt (visited), các ô đang chờ duyệt trong hàng đợi (frontier).

*   **Greedy Best-First Search**:
    *   **Loại**: Tìm kiếm có thông tin (Informed Search), Heuristic Search.
    *   **Đặc điểm**: Sử dụng một hàm heuristic (thường là khoảng cách Manhattan hoặc Euclid đến đích) để ưu tiên mở rộng các nút có vẻ gần đích nhất. Nhanh chóng tìm ra đường đi nhưng không đảm bảo là tối ưu về chi phí hoặc số bước.
    *   **Hiển thị**: Các ô đã duyệt, frontier (thường là hàng đợi ưu tiên), và đường đi dự kiến.

*   **A\* Search (A-Star)**:
    *   **Loại**: Tìm kiếm có thông tin, Heuristic Search.
    *   **Đặc điểm**: Kết hợp ưu điểm của BFS (Dijkstra - chi phí thực tế từ điểm bắt đầu, `g(n)`) và Greedy Search (chi phí ước lượng đến đích, `h(n)`). Đánh giá nút dựa trên `f(n) = g(n) + h(n)`. Nếu hàm heuristic là "nhất quán" (consistent) hoặc "chấp nhận được" (admissible), A\* đảm bảo tìm ra đường đi có chi phí thấp nhất.
    *   **Hiển thị**: Tương tự như Greedy Search, bao gồm chi phí `g` và `f` có thể được xem xét trong quá trình trực quan hóa (nếu được triển khai).

*   **Simulated Annealing (SA)**:
    *   **Loại**: Tìm kiếm cục bộ ngẫu nhiên (Randomized Local Search), Metaheuristic.
    *   **Đặc điểm**: Bắt đầu với một giải pháp ngẫu nhiên và từ từ "làm nguội" hệ thống. Ở nhiệt độ cao, thuật toán có khả năng chấp nhận các bước đi làm xấu giải pháp hiện tại để thoát khỏi tối ưu cục bộ. Khi nhiệt độ giảm, khả năng này giảm dần. Thường dùng cho các bài toán tối ưu hóa phức tạp.
    *   **Hiển thị**: Đường đi hiện tại đang được khám phá và thay đổi.

*   **Local Beam Search (LBS)**:
    *   **Loại**: Tìm kiếm cục bộ.
    *   **Đặc điểm**: Duy trì `k` trạng thái tốt nhất tại mỗi bước. Từ `k` trạng thái này, thuật toán tạo ra tất cả các trạng thái kế tiếp và chọn ra `k` trạng thái tốt nhất mới từ đó. Ít bị mắc kẹt ở tối ưu cục bộ hơn Hill Climbing đơn giản.
    *   **Hiển thị**: Các "tia" (beams) hoặc các đường đi song song đang được khám phá.

*   **Stochastic Partially Observable Solver (SPO)**:
    *   **Loại**: Lập kế hoạch trong môi trường bất định và quan sát được một phần (POMDP-like).
    *   **Đặc điểm**: Agent không biết chắc vị trí hiện tại của mình mà duy trì một "trạng thái niềm tin" (belief state) - một phân phối xác suất trên các ô. Hành động được chọn dựa trên niềm tin này, và niềm tin được cập nhật sau mỗi hành động và quan sát.
    *   **Hiển thị**: Quan trọng nhất là **bản đồ niềm tin (belief map)**, thể hiện xác suất agent tin rằng nó đang ở mỗi ô.

*   **Constraint Satisfaction Problem (CSP) with Forward Checking**:
    *   **Loại**: Tìm kiếm dựa trên ràng buộc.
    *   **Đặc điểm**: Bài toán giải mê cung được mô hình hóa như một CSP, trong đó các biến là các bước trong đường đi, và các ràng buộc là các quy tắc di chuyển hợp lệ (không đi vào tường, phải đến đích). Forward Checking là một kỹ thuật để sớm phát hiện các nhánh tìm kiếm không khả thi.
    *   **Hiển thị**: Đường đi đang được xây dựng từng bước, và có thể hiển thị các "miền giá trị" (domains) của các biến đang bị thu hẹp bởi Forward Checking.

*   **Q-Learning**:
    *   **Loại**: Học tăng cường (Reinforcement Learning), Học không cần mô hình (Model-Free).
    *   **Đặc điểm**: Agent học một hàm giá trị hành động (Q-value) cho mỗi cặp (trạng thái, hành động) thông qua tương tác thử và sai với môi trường (mê cung). Q-value ước tính phần thưởng kỳ vọng khi thực hiện một hành động tại một trạng thái và tuân theo chính sách tối ưu sau đó.
    *   **Hiển thị**: Quá trình huấn luyện (các tập - episodes), và sau đó là đường đi được suy ra từ Q-table đã học. Bản đồ giá trị (value map) từ Q-table cũng có thể được hiển thị.

## Cài Đặt và Chạy

1.  **Yêu cầu**:
    *   Python 3.x
    *   Pygame: `pip install pygame`

2.  **Tải xuống**:
    *   Clone repository này: `git clone https://github.com/trihieuvo/escape_room.git`
    *   Hoặc tải về dưới dạng file ZIP và giải nén.

3.  **Chạy Game**:
    *   Điều hướng đến thư mục gốc của dự án trong terminal.
    *   Chạy lệnh: `python main.py`

## Cách Chơi và Sử Dụng

*   **Giao Diện Chính**:
    *   **Khu vực Mê Cung (Trái)**: Hiển thị mê cung, nhân vật, và các đối tượng.
    *   **Khu vực Thông Tin (Phải)**: Hiển thị trạng thái hiện tại, thông số của thuật toán/người chơi. Trong chế độ SPO, bản đồ niềm tin sẽ hiển thị ở đây.
    *   **Khu vực Điều Khiển (Dưới)**:
        *   **Solver Mode**: Chọn "Player" hoặc một trong các thuật toán.
        *   **Maze Parameters**: Thiết lập số lượng chìa khóa mong muốn (ảnh hưởng đến số lượng bùn, đường trượt, cổng dịch chuyển).
        *   **Speed**: Điều chỉnh tốc độ của game và quá trình trực quan hóa thuật toán.
        *   **Actions**:
            *   `Regenerate`: Tạo một mê cung mới với các thông số đã chọn.
            *   `Start Run`: Bắt đầu chạy với chế độ (Player/Algorithm) đã chọn.
            *   `Compare`: (Chỉ khả dụng sau khi có ít nhất một lần chạy trên mê cung hiện tại) Mở màn hình so sánh kết quả.

*   **Điều Khiển Người Chơi (Player Mode)**:
    *   Sử dụng các phím mũi tên (Lên, Xuống, Trái, Phải) hoặc các phím `W, A, S, D` để di chuyển.
    *   Thu thập đủ chìa khóa và đi đến ô màu xanh lá (Exit) để chiến thắng.

*   **Màn Hình So Sánh**:
    *   Hiển thị bảng chi tiết và tóm tắt hiệu suất của các thuật toán.
    *   Nhấn `ESC` hoặc `ENTER` để quay lại.

*   **Thoát Game**: Nhấn phím `ESC` khi đang ở màn hình cấu hình (IDLE_CONFIG) hoặc màn hình so_sánh/kết_thúc.

## Tác Giả (Nhóm Phát Triển)

*   Võ Trí Hiệu
*   Lê Ngô Nhựt Tân
*   Nguyễn Bảo Lợi

**Email liên hệ**: hieu981.vn@gmail.com

