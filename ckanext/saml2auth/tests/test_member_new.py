import pytest

import ckan.tests.factories as factories
from ckan.plugins.toolkit import url_for


@pytest.mark.ckan_config('ckan.plugins', 'saml2auth')
@pytest.mark.usefixtures('with_plugins', 'clean_db')
def test_organization_member_form_only_offers_existing_users(app):
    organization = factories.Organization()
    admin = factories.Sysadmin()

    response = app.get(
        url_for('organization.member_new', id=organization['name']),
        extra_environ={'REMOTE_USER': admin['name']},
    )
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'Existing User' in page
    assert 'New User' not in page
    assert 'name="email"' not in page
