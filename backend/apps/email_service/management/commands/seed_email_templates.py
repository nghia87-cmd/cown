"""
Management command to seed email templates
"""

from django.core.management.base import BaseCommand
from apps.email_service.models import EmailTemplate


class Command(BaseCommand):
    help = 'Seed email templates for the platform'

    def handle(self, *args, **options):
        templates = [
            {
                'name': 'welcome_email',
                'code': 'WELCOME_EMAIL',
                'category': 'AUTHENTICATION',
                'subject': 'Chào mừng đến với COWN - Nền tảng tuyển dụng',
                'html_content': '''
                    <h1>Xin chào {{user_name}}!</h1>
                    <p>Chào mừng bạn đến với COWN - Nền tảng tuyển dụng hàng đầu Việt Nam.</p>
                    <p>Tài khoản của bạn đã được tạo thành công với email: <strong>{{user_email}}</strong></p>
                    <p>Hãy bắt đầu hành trình tìm kiếm công việc mơ ước của bạn ngay hôm nay!</p>
                    <a href="{{verify_link}}" style="background: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                        Xác thực Email
                    </a>
                    <p>Hoặc sao chép link sau: {{verify_link}}</p>
                    <p>Trân trọng,<br>Đội ngũ COWN</p>
                ''',
                'text_content': 'Xin chào {{user_name}}! Chào mừng bạn đến với COWN. Link xác thực: {{verify_link}}',
                'variables': ['user_name', 'user_email', 'verify_link'],
                'description': 'Email chào mừng người dùng mới'
            },
            {
                'name': 'email_verification',
                'code': 'EMAIL_VERIFICATION',
                'category': 'AUTHENTICATION',
                'subject': 'Xác thực Email - COWN',
                'html_content': '''
                    <h2>Xác thực Email của bạn</h2>
                    <p>Xin chào {{user_name}},</p>
                    <p>Vui lòng click vào nút bên dưới để xác thực email của bạn:</p>
                    <a href="{{verify_link}}" style="background: #2196F3; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        Xác thực Email
                    </a>
                    <p>Link này sẽ hết hạn sau 24 giờ.</p>
                    <p>Nếu bạn không yêu cầu xác thực này, vui lòng bỏ qua email này.</p>
                ''',
                'text_content': 'Xác thực email: {{verify_link}}',
                'variables': ['user_name', 'verify_link'],
                'description': 'Email xác thực tài khoản'
            },
            {
                'name': 'password_reset',
                'code': 'PASSWORD_RESET',
                'category': 'AUTHENTICATION',
                'subject': 'Đặt lại mật khẩu - COWN',
                'html_content': '''
                    <h2>Đặt lại mật khẩu</h2>
                    <p>Xin chào {{user_name}},</p>
                    <p>Chúng tôi nhận được yêu cầu đặt lại mật khẩu cho tài khoản của bạn.</p>
                    <a href="{{reset_link}}" style="background: #FF9800; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        Đặt lại mật khẩu
                    </a>
                    <p>Link này sẽ hết hạn sau 1 giờ.</p>
                    <p>Nếu bạn không yêu cầu đặt lại mật khẩu, vui lòng bỏ qua email này.</p>
                ''',
                'text_content': 'Đặt lại mật khẩu: {{reset_link}}',
                'variables': ['user_name', 'reset_link'],
                'description': 'Email đặt lại mật khẩu'
            },
            {
                'name': 'application_received',
                'code': 'APPLICATION_RECEIVED',
                'category': 'APPLICATION',
                'subject': 'Đơn ứng tuyển của bạn đã được nhận',
                'html_content': '''
                    <h2>Đơn ứng tuyển đã được gửi thành công!</h2>
                    <p>Xin chào {{candidate_name}},</p>
                    <p>Đơn ứng tuyển của bạn cho vị trí <strong>{{job_title}}</strong> tại <strong>{{company_name}}</strong> đã được nhận.</p>
                    <p><strong>Chi tiết:</strong></p>
                    <ul>
                        <li>Vị trí: {{job_title}}</li>
                        <li>Công ty: {{company_name}}</li>
                        <li>Ngày nộp: {{applied_date}}</li>
                        <li>Trạng thái: Đang xem xét</li>
                    </ul>
                    <p>Nhà tuyển dụng sẽ xem xét hồ sơ của bạn và liên hệ sớm nhất có thể.</p>
                    <a href="{{application_link}}">Xem đơn ứng tuyển</a>
                ''',
                'text_content': 'Đơn ứng tuyển {{job_title}} tại {{company_name}} đã được nhận.',
                'variables': ['candidate_name', 'job_title', 'company_name', 'applied_date', 'application_link'],
                'description': 'Email xác nhận đã nhận đơn ứng tuyển'
            },
            {
                'name': 'application_status_update',
                'code': 'APPLICATION_STATUS_UPDATE',
                'category': 'APPLICATION',
                'subject': 'Cập nhật trạng thái đơn ứng tuyển',
                'html_content': '''
                    <h2>Cập nhật đơn ứng tuyển</h2>
                    <p>Xin chào {{candidate_name}},</p>
                    <p>Có cập nhật mới về đơn ứng tuyển của bạn:</p>
                    <p><strong>Vị trí:</strong> {{job_title}}<br>
                    <strong>Công ty:</strong> {{company_name}}<br>
                    <strong>Trạng thái mới:</strong> <span style="color: #4CAF50; font-weight: bold;">{{new_status}}</span></p>
                    {{#if message}}
                    <p><strong>Tin nhắn từ nhà tuyển dụng:</strong><br>{{message}}</p>
                    {{/if}}
                    <a href="{{application_link}}" style="background: #2196F3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                        Xem chi tiết
                    </a>
                ''',
                'text_content': 'Đơn ứng tuyển {{job_title}} có trạng thái mới: {{new_status}}',
                'variables': ['candidate_name', 'job_title', 'company_name', 'new_status', 'message', 'application_link'],
                'description': 'Email thông báo thay đổi trạng thái đơn'
            },
            {
                'name': 'interview_scheduled',
                'code': 'INTERVIEW_SCHEDULED',
                'category': 'APPLICATION',
                'subject': 'Lịch phỏng vấn - {{job_title}}',
                'html_content': '''
                    <h2>Lời mời phỏng vấn</h2>
                    <p>Xin chào {{candidate_name}},</p>
                    <p>Chúc mừng! Bạn đã được mời tham gia phỏng vấn cho vị trí <strong>{{job_title}}</strong> tại <strong>{{company_name}}</strong>.</p>
                    <p><strong>Thông tin phỏng vấn:</strong></p>
                    <ul>
                        <li>Loại: {{interview_type}}</li>
                        <li>Thời gian: {{interview_datetime}}</li>
                        <li>Thời lượng: {{duration}} phút</li>
                        {{#if location}}
                        <li>Địa điểm: {{location}}</li>
                        {{/if}}
                        {{#if meeting_link}}
                        <li>Link phỏng vấn: <a href="{{meeting_link}}">{{meeting_link}}</a></li>
                        {{/if}}
                    </ul>
                    {{#if description}}
                    <p><strong>Mô tả:</strong><br>{{description}}</p>
                    {{/if}}
                    <p>Vui lòng chuẩn bị kỹ lưỡng và tham gia đúng giờ. Chúc bạn may mắn!</p>
                ''',
                'text_content': 'Lịch phỏng vấn {{job_title}} vào {{interview_datetime}}',
                'variables': ['candidate_name', 'job_title', 'company_name', 'interview_type', 'interview_datetime', 'duration', 'location', 'meeting_link', 'description'],
                'description': 'Email lịch phỏng vấn'
            },
            {
                'name': 'interview_reminder',
                'code': 'INTERVIEW_REMINDER',
                'category': 'APPLICATION',
                'subject': 'Nhắc nhở: Phỏng vấn vào {{interview_time}}',
                'html_content': '''
                    <h2>Nhắc nhở phỏng vấn</h2>
                    <p>Xin chào {{candidate_name}},</p>
                    <p>Đây là lời nhắc về buổi phỏng vấn sắp tới của bạn:</p>
                    <p><strong>Vị trí:</strong> {{job_title}}<br>
                    <strong>Công ty:</strong> {{company_name}}<br>
                    <strong>Thời gian:</strong> {{interview_datetime}}<br>
                    <strong>Còn lại:</strong> 24 giờ</p>
                    {{#if meeting_link}}
                    <a href="{{meeting_link}}" style="background: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                        Tham gia phỏng vấn
                    </a>
                    {{/if}}
                    <p>Hãy chuẩn bị sẵn sàng và tham gia đúng giờ nhé!</p>
                ''',
                'text_content': 'Nhắc nhở: Phỏng vấn {{job_title}} vào {{interview_datetime}}',
                'variables': ['candidate_name', 'job_title', 'company_name', 'interview_datetime', 'meeting_link'],
                'description': 'Email nhắc nhở trước phỏng vấn 24h'
            },
            {
                'name': 'new_job_match',
                'code': 'NEW_JOB_MATCH',
                'category': 'JOB',
                'subject': 'Công việc mới phù hợp với bạn!',
                'html_content': '''
                    <h2>Có việc làm mới phù hợp với bạn!</h2>
                    <p>Xin chào {{user_name}},</p>
                    <p>Chúng tôi tìm thấy {{job_count}} việc làm phù hợp với hồ sơ của bạn:</p>
                    {{#each jobs}}
                    <div style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px;">
                        <h3>{{this.title}}</h3>
                        <p><strong>{{this.company}}</strong> - {{this.location}}</p>
                        <p>Mức lương: {{this.salary}}</p>
                        <p>Độ phù hợp: {{this.match_score}}%</p>
                        <a href="{{this.link}}">Xem chi tiết</a>
                    </div>
                    {{/each}}
                    <a href="{{more_jobs_link}}" style="background: #2196F3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                        Xem thêm việc làm
                    </a>
                ''',
                'text_content': 'Có {{job_count}} việc làm mới phù hợp với bạn!',
                'variables': ['user_name', 'job_count', 'jobs', 'more_jobs_link'],
                'description': 'Email gợi ý việc làm phù hợp'
            },
            {
                'name': 'job_alert',
                'code': 'JOB_ALERT',
                'category': 'JOB',
                'subject': 'Thông báo việc làm - {{alert_name}}',
                'html_content': '''
                    <h2>Thông báo việc làm mới</h2>
                    <p>Xin chào {{user_name}},</p>
                    <p>Có {{job_count}} việc làm mới phù hợp với tiêu chí "<strong>{{alert_name}}</strong>" của bạn:</p>
                    {{#each jobs}}
                    <div style="border-left: 3px solid #4CAF50; padding-left: 15px; margin: 15px 0;">
                        <h3>{{this.title}}</h3>
                        <p><strong>{{this.company}}</strong></p>
                        <p>📍 {{this.location}} | 💰 {{this.salary}} | ⏰ {{this.posted_date}}</p>
                        <a href="{{this.link}}">Ứng tuyển ngay</a>
                    </div>
                    {{/each}}
                ''',
                'text_content': 'Có {{job_count}} việc làm mới cho "{{alert_name}}"',
                'variables': ['user_name', 'alert_name', 'job_count', 'jobs'],
                'description': 'Email thông báo job alert'
            },
            {
                'name': 'new_message',
                'code': 'NEW_MESSAGE',
                'category': 'NOTIFICATION',
                'subject': 'Tin nhắn mới từ {{sender_name}}',
                'html_content': '''
                    <h2>Tin nhắn mới</h2>
                    <p>Xin chào {{recipient_name}},</p>
                    <p><strong>{{sender_name}}</strong> đã gửi tin nhắn cho bạn:</p>
                    <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 15px 0;">
                        "{{message_preview}}"
                    </div>
                    <a href="{{conversation_link}}" style="background: #2196F3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                        Trả lời ngay
                    </a>
                ''',
                'text_content': '{{sender_name}}: {{message_preview}}',
                'variables': ['recipient_name', 'sender_name', 'message_preview', 'conversation_link'],
                'description': 'Email thông báo tin nhắn mới'
            },
            {
                'name': 'daily_digest',
                'code': 'DAILY_DIGEST',
                'category': 'NOTIFICATION',
                'subject': 'Tóm tắt hoạt động hôm nay - COWN',
                'html_content': '''
                    <h2>Tóm tắt ngày {{date}}</h2>
                    <p>Xin chào {{user_name}},</p>
                    <p>Đây là tóm tắt hoạt động của bạn hôm nay:</p>
                    
                    {{#if has_notifications}}
                    <h3>🔔 Thông báo ({{notification_count}})</h3>
                    <ul>
                        {{#each notifications}}
                        <li>{{this.message}}</li>
                        {{/each}}
                    </ul>
                    {{/if}}
                    
                    {{#if has_messages}}
                    <h3>💬 Tin nhắn ({{message_count}})</h3>
                    <ul>
                        {{#each messages}}
                        <li><strong>{{this.sender}}:</strong> {{this.preview}}</li>
                        {{/each}}
                    </ul>
                    {{/if}}
                    
                    {{#if has_job_matches}}
                    <h3>💼 Việc làm phù hợp ({{job_match_count}})</h3>
                    <ul>
                        {{#each job_matches}}
                        <li><a href="{{this.link}}">{{this.title}}</a> tại {{this.company}}</li>
                        {{/each}}
                    </ul>
                    {{/if}}
                    
                    <a href="{{dashboard_link}}">Xem tất cả</a>
                ''',
                'text_content': 'Tóm tắt ngày {{date}}: {{notification_count}} thông báo, {{message_count}} tin nhắn',
                'variables': ['user_name', 'date', 'has_notifications', 'notification_count', 'notifications', 'has_messages', 'message_count', 'messages', 'has_job_matches', 'job_match_count', 'job_matches', 'dashboard_link'],
                'description': 'Email tóm tắt hàng ngày'
            },
        ]

        created_count = 0
        updated_count = 0

        for template_data in templates:
            template, created = EmailTemplate.objects.update_or_create(
                code=template_data['code'],
                defaults={
                    'name': template_data['name'],
                    'subject': template_data['subject'],
                    'html_content': template_data['html_content'],
                    'text_content': template_data['text_content'],
                    'variables': template_data['variables'],
                    'description': template_data['description'],
                    'category': template_data['category'],
                    'is_active': True
                }
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Created: {template.name}'))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'↻ Updated: {template.name}'))

        self.stdout.write(self.style.SUCCESS(f'\n✅ Seeding completed!'))
        self.stdout.write(self.style.SUCCESS(f'   Created: {created_count} templates'))
        self.stdout.write(self.style.SUCCESS(f'   Updated: {updated_count} templates'))
