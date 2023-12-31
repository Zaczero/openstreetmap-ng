from src.lib.auth import auth_user
from src.models.mail_from_type import MailFromType
from src.services.mail_service import MailService
from src.services.user_token_email_change_service import UserTokenEmailChangeService


class EmailChangeService:
    @staticmethod
    async def send_confirm_email(to_email: str) -> None:
        """
        Send a confirmation email for the email change.
        """

        token = await UserTokenEmailChangeService.create(to_email)

        await MailService.schedule(
            from_user=None,
            from_type=MailFromType.system,
            to_user=auth_user(),
            subject='TODO',  # TODO:
            template_name='TODO',
            template_data={'token': str(token)},
        )
