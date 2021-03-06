#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2012-2013 Zuza Software Foundation
# Copyright 2013-2014 Evernote Corporation
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

from django_assets import Bundle, register

js_common = Bundle(
    'js/vendor/jquery/jquery.js',
    'js/vendor/jquery/jquery.tipsy.js',
    'js/vendor/jquery/jquery.cookie.js',
    'js/vendor/jquery/jquery.bidi.js',
    'js/vendor/jquery/jquery.magnific-popup.js',
    'js/vendor/jquery/jquery.utils.js',
    'js/vendor/jquery/jquery.easing.js',
    'js/vendor/jquery/jquery.serializeObject.js',
    'js/vendor/jquery/jquery.select2.js',
    'js/vendor/bootstrap/bootstrap-alert.js',
    'js/vendor/bootstrap/bootstrap-transition.js',
    'js/vendor/underscore.js',
    'js/vendor/backbone/backbone.js',
    'js/vendor/odometer.js',
    'js/browser.js',
    'js/captcha.js',
    'js/common.js',
    'js/contact.js',
    'js/dropdown.js',
    'js/mixins.js',
    'js/msg.js',
    'js/search.js',
    'js/score.js',
    'js/stats.js',
    'js/utils.js',
    'js/vendor/sorttable.js',
    'js/vendor/spin.js',
    'js/vendor/shortcut.js',  # Leave shortcut.js as the last one
    filters='rjsmin', output='js/common.min.%(version)s.js')
register('js_common', js_common)

js_admin = Bundle(
    'js/admin.js',
    filters='rjsmin', output='js/admin.min.%(version)s.js')
register('js_admin', js_admin)


# <Webpack>
# These are handled by webpack and therefore have no filters applied
# They're kept here so hash-based cache invalidation can be used

js_vendor = Bundle(
    'js/vendor.bundle.js',
    output='js/vendor.min.%(version)s.js')
register('js_vendor', js_vendor)

js_admin_app = Bundle(
    'js/admin/app.bundle.js',
    output='js/admin/app.min.%(version)s.js')
register('js_admin_app', js_admin_app)


js_user_app = Bundle(
    'js/user/app.bundle.js',
    output='js/user/app.min.%(version)s.js')
register('js_user_app', js_user_app)

# </Webpack>


js_editor = Bundle(
    'js/vendor/jquery/jquery.history.js',
    'js/vendor/jquery/jquery.textarea-expander.js',
    'js/vendor/levenshtein.js',
    'js/vendor/diff_match_patch.js',
    'js/vendor/jquery/jquery.caret.js',
    'js/vendor/jquery/jquery.highlightRegex.js',
    'js/vendor/jquery/jquery.jsonp.js',
    'js/vendor/iso8601.js',
    'js/vendor/backbone/backbone-relational.js',
    'js/models.js',
    'js/collections.js',
    'js/editor.js',
    filters='rjsmin', output='js/editor.min.%(version)s.js')
register('js_editor', js_editor)

css_common = Bundle(
    'css/style.css',
    'css/actions.css',
    'css/buttons.css',
    'css/contact.css',
    'css/error.css',
    'css/login.css',
    'css/magnific-popup.css',
    'css/navbar.css',
    'css/odometer.css',
    'css/popup.css',
    'css/tipsy.css',
    'css/sprite.css',
    'css/select2.css',
    'css/select2-pootle.css',
    'css/scores.css',
    'css/user.css',
    'css/welcome.css',
    filters='cssmin', output='css/common.min.%(version)s.css')
register('css_common', css_common)

css_admin = Bundle(
    'css/admin.css',
    filters='cssmin', output='css/admin.min.%(version)s.css')
register('css_admin', css_admin)

css_editor = Bundle(
    'css/editor.css',
    filters='cssmin', output='css/editor.min.%(version)s.css')
register('css_editor', css_editor)
