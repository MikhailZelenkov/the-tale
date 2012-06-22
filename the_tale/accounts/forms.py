# coding: utf-8

from dext.forms import forms, fields

from accounts.conf import accounts_settings


class EditProfileForm(forms.Form):

    nick = fields.RegexField(label=u'Имя',
                             regex=accounts_settings.NICK_REGEX,
                             min_length=accounts_settings.NICK_MIN_LENGTH,
                             max_length=accounts_settings.NICK_MAX_LENGTH)

    email = fields.EmailField(label=u'Email (логин)')

    password = fields.PasswordField(label=u'Новый пароль',
                                    required=False)


class LoginForm(forms.Form):

    email = fields.EmailField(label=u'Email')
    password = fields.PasswordField(label=u'Пароль')


class ResetPasswordForm(forms.Form):

    email = fields.EmailField(label=u'Email')
