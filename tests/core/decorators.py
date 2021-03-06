#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2014 Evernote Corporation
#
# This file is part of Pootle.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import pytest

from django.http import Http404

from pootle.core.decorators import get_path_obj, get_resource
from pootle_app.models import Directory
from pootle_language.models import Language
from pootle_project.models import Project, ProjectResource
from pootle_store.models import Store
from pootle_translationproject.models import TranslationProject


@pytest.mark.django_db
def test_get_path_obj(rf, default, afrikaans_tutorial,
                      arabic_tutorial_disabled, tutorial_disabled):
    """Ensure the correct path object is retrieved."""
    language_code = afrikaans_tutorial.language.code
    project_code = afrikaans_tutorial.project.code

    project_code_disabled = tutorial_disabled.code

    language_code_fake = 'faf'
    project_code_fake = 'fake-tutorial'

    request = rf.get('/')
    request.user = default

    # Fake decorated function
    func = get_path_obj(lambda x, y: (x, y))

    # Single project
    func(request, project_code=project_code)
    assert isinstance(request.ctx_obj, Project)

    # Missing/disabled project
    with pytest.raises(Http404):
        func(request, project_code=project_code_fake)

    with pytest.raises(Http404):
        func(request, project_code=project_code_disabled)

    # Single language
    func(request, language_code=language_code)
    assert isinstance(request.ctx_obj, Language)

    # Missing language
    with pytest.raises(Http404):
        func(request, language_code=language_code_fake)

    # Translation Project
    func(request, language_code=language_code, project_code=project_code)
    assert isinstance(request.ctx_obj, TranslationProject)

    # Missing/disabled Translation Project
    with pytest.raises(Http404):
        func(request, language_code=language_code_fake,
             project_code=project_code)

    with pytest.raises(Http404):
        func(request, language_code=language_code,
             project_code=project_code_disabled)

    with pytest.raises(Http404):
        func(request, language_code=arabic_tutorial_disabled.language.code,
             project_code=arabic_tutorial_disabled.project.code)


def test_get_resource_tp(rf, default, tutorial, afrikaans_tutorial):
    """Tests that the correct resources are set for the given TP contexts."""
    store_name = 'tutorial.po'
    subdir_name = 'subdir/'

    subdir_name_fake = 'fake_subdir/'
    store_name_fake = 'fake_store.po'

    request = rf.get('/')
    request.user = default

    # Fake decorated function
    func = get_resource(lambda x, y, s, t: (x, y, s, t))

    # TP, no resource
    func(request, afrikaans_tutorial, '', '')
    assert isinstance(request.resource_obj, TranslationProject)

    # TP, file resource
    func(request, afrikaans_tutorial, '', store_name)
    assert isinstance(request.resource_obj, Store)

    # TP, directory resource
    func(request, afrikaans_tutorial, subdir_name, '')
    assert isinstance(request.resource_obj, Directory)

    # TP, missing file/dir resource, redirects to parent resource
    response = func(request, afrikaans_tutorial, '', store_name_fake)
    assert response.status_code == 302
    assert afrikaans_tutorial.pootle_path in response.get('location')

    response = func(request, afrikaans_tutorial, subdir_name, store_name_fake)
    assert response.status_code == 302
    assert (''.join([afrikaans_tutorial.pootle_path, subdir_name]) in
            response.get('location'))

    response = func(request, afrikaans_tutorial, subdir_name_fake, '')
    assert response.status_code == 302
    assert afrikaans_tutorial.pootle_path in response.get('location')


def test_get_resource_project(rf, default, tutorial, afrikaans_tutorial,
                              arabic_tutorial_disabled):
    """Tests that the correct resources are set for the given Project
    contexts.
    """
    store_name = 'tutorial.po'
    subdir_name = 'subdir/'

    subdir_name_fake = 'fake_subdir/'
    store_name_fake = 'fake_store.po'

    request = rf.get('/')
    request.user = default

    # Fake decorated function
    func = get_resource(lambda x, y, s, t: (x, y, s, t))

    # Project, no resource
    func(request, tutorial, '', '')
    assert isinstance(request.resource_obj, Project)

    # Project, cross-language file resource
    func(request, tutorial, '', store_name)
    assert isinstance(request.resource_obj, ProjectResource)

    # Two languages have this file, but the Arabic project is disabled!
    # Should only contain a single file resource
    assert len(request.resource_obj.resources) == 1
    assert isinstance(request.resource_obj.resources[0], Store)

    # Project, cross-language directory resource
    func(request, tutorial, subdir_name, '')
    assert isinstance(request.resource_obj, ProjectResource)

    # Two languages have this dir, but the Arabic project is disabled!
    # Should only contain a single dir resource
    assert len(request.resource_obj.resources) == 1
    assert isinstance(request.resource_obj.resources[0], Directory)
