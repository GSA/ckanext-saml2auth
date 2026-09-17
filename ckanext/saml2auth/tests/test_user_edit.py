from html.parser import HTMLParser

import pytest

import ckan.logic as logic
import ckan.model as model
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
from ckan.plugins.toolkit import url_for

from ckanext.saml2auth.views.saml2auth import _update_user


class ButtonParser(HTMLParser):
    def __init__(self):
        super(ButtonParser, self).__init__()
        self.buttons = []

    def handle_starttag(self, tag, attrs):
        if tag == 'button':
            self.buttons.append(dict(attrs))

    def button_by_name(self, name):
        return next(button for button in self.buttons
                    if button.get('name') == name)


@pytest.mark.ckan_config('ckan.plugins', 'saml2auth')
@pytest.mark.usefixtures('with_plugins', 'clean_db')
class TestUserEdit:
    def _edit_form(self, app, editor, user):
        response = app.get(
            url_for('user.edit', id=user['name']),
            extra_environ={'REMOTE_USER': editor['name']},
            status=200,
        )
        parser = ButtonParser()
        parser.feed(response.get_data(as_text=True))
        return parser

    @pytest.mark.parametrize('state', ['active', 'deleted'])
    def test_disables_profile_submit_button(self, app, state):
        sysadmin = factories.Sysadmin()
        user = factories.User(state=state)

        form = self._edit_form(app, sysadmin, user)

        button = form.button_by_name('save')
        assert button['type'] == 'button'
        assert button['aria-disabled'] == 'true'
        assert 'login.gov' in button['onclick']

    def test_blocks_user_update_action(self):
        user = factories.User(fullname='Original Name')

        with pytest.raises(logic.NotAuthorized):
            helpers.call_action(
                'user_update',
                context={'user': user['name']},
                id=user['id'],
                fullname='Changed Name',
            )

        model.Session.expire_all()
        assert model.User.get(user['id']).fullname == 'Original Name'

    def test_blocks_user_reactivation_action(self):
        user = factories.User(state='deleted')

        with pytest.raises(logic.NotAuthorized):
            helpers.call_action(
                'user_update',
                context={'user': factories.Sysadmin()['name']},
                id=user['id'],
                state='active',
            )

        model.Session.expire_all()
        assert model.User.get(user['id']).state == model.State.DELETED

    def test_allows_saml_user_sync(self):
        user = factories.User(fullname='Original Name')

        result = _update_user({
            'id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'fullname': 'SAML Name',
        })

        assert result['fullname'] == 'SAML Name'
