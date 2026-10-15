# YULEESELF — tài khoản sử dụng riêng

Bản nâng cấp dựa trên commit `3d0b59a` của `itsyulee/yulee-self`.

## Cập nhật bản đang dùng

1. Dừng hoàn toàn server cũ và các tiến trình bot. Sao lưu thư mục project, đặc biệt `config/` và `data/`.
2. Giải nén gói cập nhật vào thư mục chứa `setup.py`, chấp nhận thay thế file. Không xóa project cũ.
3. Chạy:

   ```bash
   python setup.py --quick
   ```

4. Mở `http://localhost:8000` hoặc địa chỉ hosting của bạn; nhấn Ctrl+F5.
5. Đăng nhập bằng tài khoản trong `config/auth.json` cũ. Lần chạy đầu chuyển tài khoản đó thành admin và sao chép Discord, proxy, settings, thống kê, lịch sử cũ sang vùng dữ liệu của admin. Không phát các dữ liệu này cho khách mới.

Nếu chưa có auth hoặc vẫn dùng mật khẩu mẫu mặc định, terminal yêu cầu tạo admin lần đầu. Trên hosting không có terminal tương tác, đặt `YULEESELF_ADMIN_USER` và `YULEESELF_ADMIN_PASSWORD` qua biến môi trường trước khi chạy. Mật khẩu mới cần ít nhất 8 ký tự.

Sau khi cài dependencies, có thể dùng `python yulee.py` để mở server trực tiếp. Không còn bước nhập token/proxy hoặc chọn menu Start trong setup. Web vẫn chạy khi chưa có Discord nào.

## Admin cấp quyền sau khi bán

- Đăng nhập → **Quản lý người dùng** → nhập tên đăng nhập, mật khẩu và hạn dùng nếu cần → **Lưu tài khoản**.
- Gửi thông tin đăng nhập cho khách bằng cách bạn lựa chọn. Project không tự gửi tin nhắn hay thu tiền.
- Chọn **Sửa / khóa / đặt lại mật khẩu** để gia hạn, bỏ chọn **Cho phép sử dụng**, hoặc đặt mật khẩu mới.
- Khóa tài khoản dừng worker của người đó và chặn phiên đăng nhập. Hạn dùng được kiểm tra ở mỗi yêu cầu; supervisor cũng dừng worker hết hạn.
- Admin có Discord/proxy riêng; quyền quản trị người dùng không tự mở dữ liệu Discord của khách.
- Sau khi chuyển sang bản này, không thêm khách bằng cách chỉnh `config/auth.json`. Danh tính đăng nhập mới nằm trong cơ sở dữ liệu người dùng.

## Khách sử dụng

1. Đăng nhập bằng tài khoản được cấp.
2. Vào **Proxies** để nhập proxy riêng và bấm **Test** / **Test All**.
3. Vào **Accounts → ADD ACCOUNT** để nhập tên, Discord token và Channel IDs.
4. Chọn proxy cụ thể, **Auto — chọn proxy trống đã Test OK**, hoặc **None (direct)** nếu không cần proxy. Nút **Auto-Assign** trong Proxies phân proxy của người dùng đó cho các Discord chưa có proxy.
5. Lưu: worker của người đó kết nối lại để áp dụng, không cần khởi động lại server chung. Xóa, tắt account hoặc thay proxy cũng tự áp dụng. Sau vài giây, tài khoản kết nối thành công xuất hiện ở Online.
6. Vào **Tài khoản đăng nhập → Đổi mật khẩu**. Cần mật khẩu hiện tại; các phiên cũ khác bị đăng xuất sau khi đổi.

Token đã lưu không được trả đầy đủ về trình duyệt. Khi sửa Discord, để trống token để giữ nguyên. Mỗi người dùng có settings, log, captcha, lịch sử, Discord và proxy riêng; “Save to all” chỉ áp dụng trong tài khoản đang đăng nhập.

## Dữ liệu và vận hành

- `data/service/users.sqlite3`: người dùng, mật khẩu đã băm, trạng thái và thời hạn.
- `data/service/tenants/<id>/config/`: tài khoản Discord, proxy và cấu hình của một người dùng.
- `data/service/tenants/<id>/data/`: thống kê, SQLite history, quotes và log worker của người đó.
- Mật khẩu web được băm; token Discord/proxy vẫn cần lưu trong file riêng trên server để bot sử dụng. Bảo vệ quyền truy cập máy chủ và bản sao lưu.
- Không đưa `data/service/` lên GitHub. Thư mục này đã thêm vào `.gitignore`. `.gitignore` không tự bỏ theo dõi các file nhạy cảm đã từng commit trước đó.
- Mỗi worker chỉ lắng nghe trên loopback và yêu cầu khóa riêng; chỉ gateway xác thực người dùng mới gọi được. Worker dùng chung mã nguồn nhưng tách tiến trình, bộ nhớ và thư mục làm việc.
- Mỗi người dùng có worker riêng nên RAM tăng theo số người dùng hoạt động. Bản này chạy một gateway trên một máy, không phải hệ thống phân tán nhiều máy.
- Chạy duy nhất một gateway trên cùng vùng dữ liệu. File lock chặn chạy trùng; worker sẽ dừng khi gateway mất heartbeat.
- Cổng: `PORT` hoặc `YULEESELF_PORT`, mặc định `8000`. Host: `YULEESELF_HOST`, mặc định `0.0.0.0`.
- Khi cung cấp dịch vụ qua HTTPS, đặt `YULEESELF_HTTPS=1` để cookie chỉ truyền qua HTTPS. Không bật biến này nếu đang thử bằng HTTP localhost.
- Có thể đặt `YULEESELF_SERVICE_DIR` thành đường dẫn tuyệt đối đến ổ lưu trữ bền vững của hosting.
- Nếu worker không chạy, kiểm tra `<vùng dữ liệu>/tenants/<id>/data/worker.log` trên máy chủ.
- Nếu khôi phục bản cũ, dừng gateway/workers trước rồi khôi phục cả mã nguồn và dữ liệu từ bản sao lưu. Dữ liệu legacy gốc không bị xóa bởi migration.

## Kiểm tra đã thực hiện

- Kiểm tra bằng Flask client và các worker Python thật: cách ly Discord/proxy/settings/history, từ chối ID tài khoản/proxy của người khác, API worker không chấp nhận khóa của worker khác.
- Admin tạo/khóa người dùng; khách không truy cập được admin API; hết hạn chặn đăng nhập; đổi mật khẩu vô hiệu hóa phiên cũ.
- Giới hạn đăng nhập sai, kiểm tra CSRF và chặn traversal trong settings ID.
- Tự phân proxy; giữ token khi sửa; chuyển auth/dữ liệu legacy một lần.
- Kiểm tra DOM kết hợp HTTP cho cấp tài khoản, thêm/sửa Discord, thêm proxy và đổi mật khẩu.
- Nạp thành công 22 module bot bằng thư viện Discord đúng phiên bản và cấu hình riêng, không kết nối Discord.
- Chưa thử đăng nhập Discord thật, proxy thật, hoặc cài đặt trên Windows/hosting của bạn. Không kiểm tra bố cục bằng trình duyệt thật vì môi trường không tải được Chromium.

Chạy lại bộ kiểm tra backend bằng:

```bash
python -m pip install pytest
python -m pytest -q tests/test_multiuser.py
```

Gói cập nhật chưa được push lên GitHub. Kiểm tra và commit/push các file mới sau khi áp dụng.
