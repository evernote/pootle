#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
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


import calendar
import math
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import resolve
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseBadRequest
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.html import escape
from django.utils.translation import ugettext_lazy as _
from django.views.generic import View
from django.views.generic.detail import SingleObjectMixin

from pootle.core.decorators import admin_required
from pootle.models.user import CURRENCIES
from pootle_misc.util import ajax_required, jsonify
from pootle_profile.views import (NoDefaultUserMixin, TestUserFieldMixin,
                                  DetailView)
from pootle_statistics.models import ScoreLog

from .forms import UserRatesForm, PaidTaskForm
from .models import PaidTask, PaidTaskTypes


# Django field query aliases
LANG_CODE = 'translation_project__language__code'
LANG_NAME = 'translation_project__language__fullname'
PRJ_CODE = 'translation_project__project__code'
PRJ_NAME = 'translation_project__project__fullname'
INITIAL = 'old_value'
POOTLE_WORDCOUNT = 'unit__source_wordcount'

SCORE_TRANSLATION_PROJECT = 'submission__translation_project'

# field aliases
DATE = 'creation_time_date'

STAT_FIELDS = ['n1']
INITIAL_STATES = ['new', 'edit']


class UserReportView(NoDefaultUserMixin, TestUserFieldMixin, DetailView):
    model = get_user_model()
    slug_field = 'username'
    slug_url_kwarg = 'username'
    template_name = 'user/report.html'

    def get_context_data(self, **kwargs):
        context = super(UserReportView, self).get_context_data(**kwargs)
        context.update({
            'paid_task_form': PaidTaskForm(),
            'now': timezone.now().strftime('%Y-%m-%d %H-%M-%S'),
        })

        return context


class UserActivityView(NoDefaultUserMixin, TestUserFieldMixin, SingleObjectMixin, View):
    model = get_user_model()
    slug_field = 'username'
    slug_url_kwarg = 'username'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.month = request.GET.get('month', None)
        return super(UserActivityView, self).dispatch(request, *args, **kwargs)

    def get(self, *args, **kwargs):
        data = get_activity_data(self.get_object(), self.month)
        return HttpResponse(jsonify(data), content_type="application/json")


class UserDetailedReportView(NoDefaultUserMixin, TestUserFieldMixin, DetailView):
    model = get_user_model()
    slug_field = 'username'
    slug_url_kwarg = 'username'
    template_name = 'user/detailed_report.html'

    def dispatch(self, request, *args, **kwargs):
        self.month = request.GET.get('month', None)
        self.url_name = resolve(request.path_info).url_name
        return super(UserDetailedReportView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(UserDetailedReportView, self).get_context_data(**kwargs)
        context.update(get_detailed_report_context(user=self.get_object(), month=self.month))
        context.update({'url_name': self.url_name})

        return context


@admin_required
def evernote_reports(request):
    User = get_user_model()

    ctx = {
        'users': jsonify(map(
            lambda x: {'id': x.username, 'text': escape(x.formatted_name)},
            User.objects.hide_meta()
        )),
        'user_rates_form': UserRatesForm(),
        'paid_task_form': PaidTaskForm(),
        'now': timezone.now().strftime('%Y-%m-%d %H-%M-%S'),
    }

    return render_to_response('admin/reports.html', ctx,
                              context_instance=RequestContext(request))


def get_detailed_report_context(user, month):
    [start, end] = get_date_interval(month)

    scores = []
    totals = {'translated': {}, 'reviewed': {}, 'total': 0}

    if user and start and end:
        scores = ScoreLog.objects \
            .select_related('submission__unit__store') \
            .filter(user=user,
                    creation_time__gte=start,
                    creation_time__lte=end) \
            .order_by('creation_time')

        scores = list(scores)

        for score in scores:
            translated, reviewed = score.get_paid_words()
            if translated is not None:
                score.action = PaidTask.get_task_type_title(PaidTaskTypes.TRANSLATION)
                score.subtotal = score.rate * translated
                score.words = translated

                if score.rate in totals['translated']:
                    totals['translated'][score.rate]['words'] += translated
                else:
                    totals['translated'][score.rate] = {'words': translated}

            elif reviewed is not None:
                score.action = PaidTask.get_task_type_title(PaidTaskTypes.REVIEW)
                score.subtotal = score.review_rate * reviewed
                score.words = score.wordcount
                if score.review_rate in totals['reviewed']:
                    totals['reviewed'][score.review_rate]['words'] += reviewed
                else:
                    totals['reviewed'][score.review_rate] = {'words': reviewed}

            score.similarity = score.get_similarity() * 100

        totals['all'] = 0

        for rate, words in totals['translated'].items():
            totals['translated'][rate]['words'] = int(math.ceil(totals['translated'][rate]['words']))
            totals['translated'][rate]['subtotal'] = rate * totals['translated'][rate]['words']
            totals['all'] += totals['translated'][rate]['subtotal']

        for rate, words in totals['reviewed'].items():
            totals['reviewed'][rate]['words'] = int(math.ceil(totals['reviewed'][rate]['words']))
            totals['reviewed'][rate]['subtotal'] = rate * totals['reviewed'][rate]['words']
            totals['all'] += totals['reviewed'][rate]['subtotal']

        totals['all'] = totals['all']

    if user != '' and user.currency is None:
        user.currency = CURRENCIES[0][0]

    return {
        'scores': scores,
        'object': user,
        'start': start,
        'end': end,
        'next': start.replace(day=1) + timedelta(days=31),
        'previous': start.replace(day=1) - timedelta(days=1),
        'totals': totals,
        'utc_offset': start.strftime("%z"),
    }


@admin_required
def evernote_reports_detailed(request):
    username = request.GET.get('username', None)
    month = request.GET.get('month', None)
    User = get_user_model()

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        user = ''

    ctx = get_detailed_report_context(user=user, month=month)
    return render_to_response('admin/detailed_reports.html', ctx,
                              context_instance=RequestContext(request))


def get_date_interval(month):
    now = start = end = timezone.now()
    if month is None:
        month = start.strftime('%Y-%m')

    try:
        start = datetime.strptime(month, '%Y-%m')
        if settings.USE_TZ:
            tz = timezone.get_default_timezone()
            start = timezone.make_aware(start, tz)
        if start < now:
            if start.month != now.month or start.year != now.year:
                end = get_max_month_datetime(start)
        else:
            end = start

        start = start.replace(hour=0, minute=0, second=0)
        end = end.replace(hour=23, minute=59, second=59)
    except ValueError:
        pass

    return [start, end]


def get_max_month_datetime(dt):
    next_month = dt.replace(day=1) + timedelta(days=31)

    return next_month.replace(day=1, hour=23, minute=59, second=59) - \
        timedelta(days=1)


def get_min_month_datetime(dt):
    return dt.replace(day=1, hour=0, minute=0, second=0)


@ajax_required
@admin_required
def update_user_rates(request):
    form = UserRatesForm(request.POST)

    if form.is_valid():
        try:
            User = get_user_model()
            user = User.objects.get(username=form.cleaned_data['username'])
        except User.DoesNotExist:
            error_text = _("User %s not found" % form.cleaned_data['username'])

            return HttpResponseNotFound(jsonify({'msg': error_text}),
                                        content_type="application/json")

        user.currency = form.cleaned_data['currency']
        user.rate = form.cleaned_data['rate']
        user.review_rate = form.cleaned_data['review_rate']
        user.hourly_rate = form.cleaned_data['hourly_rate']

        scorelog_filter = {'user': user}
        paid_task_filter = scorelog_filter.copy()
        if form.cleaned_data['effective_from'] is not None:
            effective_from = form.cleaned_data['effective_from']
            scorelog_filter.update({
                'creation_time__gte': effective_from
            })
            paid_task_filter.update({
                'date__gte': effective_from
            })

        scorelog_query = ScoreLog.objects.filter(**scorelog_filter)
        scorelog_count = scorelog_query.count()

        paid_task_query = PaidTask.objects.filter(**paid_task_filter)
        paid_task_count = paid_task_query.count()

        scorelog_query.update(rate=user.rate, review_rate=user.review_rate)

        def get_task_rate_for(user, task_type):
            return {
                PaidTaskTypes.TRANSLATION: user.rate,
                PaidTaskTypes.REVIEW: user.review_rate,
                PaidTaskTypes.HOURLY_WORK: user.hourly_rate,
            }.get(task_type, 0)

        for task in paid_task_query:
            task.rate = get_task_rate_for(user, task.task_type)
            task.save()

        user.save()

        return HttpResponse(
            jsonify({
                'scorelog_count': scorelog_count,
                'paid_task_count': paid_task_count
            }), content_type="application/json")

    return HttpResponseBadRequest(jsonify({'errors': form.errors}),
                                  content_type="application/json")


@ajax_required
@admin_required
def add_paid_task(request):
    form = PaidTaskForm(request.POST)
    if form.is_valid():
        form.save()

        return HttpResponse(jsonify({'result': form.instance.id}),
                            content_type="application/json")

    return HttpResponseBadRequest(jsonify({'errors': form.errors}),
                                  content_type="application/json")


@ajax_required
@admin_required
def remove_paid_task(request, task_id=None):
    if request.method == 'DELETE':
        tasks = PaidTask.objects.filter(id=task_id)
        count = tasks.count()
        tasks.delete()

        return HttpResponse(jsonify({'removed': count}),
                            content_type="application/json")

    return HttpResponseBadRequest(
        jsonify({'error': _('Invalid request method')}),
        content_type="application/json"
    )


def get_activity_data(user, month):
    [start, end] = get_date_interval(month)

    json = {}
    user_dict = {
        'id': user.id,
        'username': user.username,
        'formatted_name': user.formatted_name,
        'currency': user.currency if user.currency else CURRENCIES[0][0],
        'rate': user.rate,
        'review_rate': user.review_rate,
        'hourly_rate': user.hourly_rate,
    } if user != '' else user

    json['meta'] = {
        'user': user_dict,
        'month': month,
        'now': timezone.now().strftime('%Y-%m-%d %H-%M-%S'),
        'start': start.strftime('%Y-%m-%d'),
        'end': end.strftime('%Y-%m-%d'),
    }
    if user != '':
        json['summary'] = get_summary(user, start, end)
        json['grouped'] = get_grouped_paid_words(user, start, end)
        json['paid_tasks'] = get_paid_tasks(user, start, end)
        json['daily'] = get_daily_activity(user, start, end)

    return json


@ajax_required
@admin_required
def user_date_prj_activity(request):
    username = request.GET.get('username', None)
    month = request.GET.get('month', None)

    try:
        User = get_user_model()
        user = User.objects.get(username=username)
    except:
        user = ''

    json = get_activity_data(user, month)
    response = jsonify(json)

    return HttpResponse(response, content_type="application/json")


def get_daily_activity(user, start, end):
    result_translated = {
        'label': PaidTask.get_task_type_title(
            PaidTaskTypes.TRANSLATION),
        'data': [],
    }
    result_reviewed = {
        'label': PaidTask.get_task_type_title(
            PaidTaskTypes.REVIEW),
        'data': [],
    }

    result = {
        'data': [result_translated, result_reviewed],
        'max_day_score': 10,
        'min_ts': "%d" % (calendar.timegm(start.timetuple()) * 1000),
        'max_ts': "%d" % (calendar.timegm(end.timetuple()) * 1000),
        'nonempty': False,
    }

    scores = ScoreLog.objects \
                     .filter(user=user,
                             creation_time__gte=start,
                             creation_time__lte=end) \
                     .order_by('creation_time')

    saved_date = None
    current_day_score = 0
    tz = timezone.get_default_timezone()
    translated_group = {}
    reviewed_group = {}
    for score in scores:
        score_time = score.creation_time
        if settings.USE_TZ:
            score_time = timezone.make_naive(score_time, tz)
        date = score_time.date()

        translated, reviewed = score.get_paid_words()
        if translated or reviewed:
            translated = 0 if translated is None else translated
            reviewed = 0 if reviewed is None else reviewed

            if saved_date != date:
                saved_date = date
                reviewed_group[date] = 0
                translated_group[date] = 0
                if result['max_day_score'] < current_day_score:
                    result['max_day_score'] = current_day_score
                current_day_score = 0
            current_day_score += int(reviewed + translated)
            result['nonempty'] |= current_day_score > 0

            translated_group[date] += translated
            reviewed_group[date] += reviewed

    if result['max_day_score'] < current_day_score:
        result['max_day_score'] = current_day_score

    for date, item in sorted(translated_group.items(), key=lambda x: x[0]):
        ts = int(calendar.timegm(date.timetuple()) * 1000)
        result_translated['data'].append((ts, item))

    for date, item in sorted(reviewed_group.items(), key=lambda x: x[0]):
        ts = int(calendar.timegm(date.timetuple()) * 1000)
        result_reviewed['data'].append((ts, item))

    return result


def get_paid_tasks(user, start, end):
    result = []

    tasks = PaidTask.objects \
        .filter(user=user,
                date__gte=start,
                date__lte=end) \
        .order_by('pk')

    for task in tasks:
        result.append({
            'id': task.id,
            'description': task.description,
            'amount': task.amount,
            'type': task.task_type,
            'action': PaidTask.get_task_type_title(task.task_type),
            'rate': task.rate,
        })

    return result


def get_grouped_paid_words(user, start, end):
    result = []
    scores = ScoreLog.objects \
        .select_related('submission__translation_project__project',
                        'submission__translation_project__language',) \
        .filter(user=user,
                creation_time__gte=start,
                creation_time__lte=end) \
        .order_by(SCORE_TRANSLATION_PROJECT)
    tp = None
    for score in scores:
        if tp != score.submission.translation_project:
            tp = score.submission.translation_project
            row = {
                'translation_project': u'%s / %s' %
                    (tp.project.fullname, tp.language.fullname),
                'score_delta': 0,
                'translated': 0,
                'reviewed': 0,
            }
            result.append(row)

        translated_words, reviewed_words = score.get_paid_words()
        if translated_words:
            row['translated'] += translated_words
        if reviewed_words:
            row['reviewed'] += reviewed_words
        row['score_delta'] += score.score_delta

    return sorted(result, key=lambda x: x['translation_project'])


def get_summary(user, start, end):
    rate = review_rate = None
    translation_month = review_month = None
    translated_row = reviewed_row = None

    translations = []
    reviews = []

    scores = ScoreLog.objects \
        .filter(user=user,
                creation_time__gte=start,
                creation_time__lte=end) \
        .order_by('creation_time')

    tz = timezone.get_default_timezone()
    for score in scores:
        if settings.USE_TZ:
            score_time = timezone.make_naive(score.creation_time, tz)

        if (score.rate != rate or
            translation_month != score_time.month):
            rate = score.rate
            translation_month = score_time.month
            translated_row = {
                'type': PaidTaskTypes.TRANSLATION,
                'action': PaidTaskTypes.TRANSLATION,
                'amount': 0,
                'rate': score.rate,
                'start': score_time,
                'end': score_time,
            }
            translations.append(translated_row)
        if (score.review_rate != review_rate or
            review_month != score_time.month):
            review_rate = score.review_rate
            review_month = score_time.month
            reviewed_row = {
                'type': PaidTaskTypes.REVIEW,
                'action': PaidTaskTypes.REVIEW,
                'amount': 0,
                'rate': score.review_rate,
                'start': score_time,
                'end': score_time,
            }
            reviews.append(reviewed_row)

        translated_words, reviewed_words = score.get_paid_words()

        if translated_words > 0:
            translated_row['end'] = score_time
            translated_row['amount'] += translated_words
        elif reviewed_words > 0:
            reviewed_row['end'] = score_time
            reviewed_row['amount'] += reviewed_words

    for group in [translations, reviews]:
        for i, item in enumerate(group):
            if i == 0:
                item['start'] = start
            else:
                item['start'] = get_min_month_datetime(item['start'])

            if item['end'].month == end.month and item['end'].year == end.year:
                item['end'] = end
            else:
                item['end'] = get_max_month_datetime(item['end'])

    result = filter(lambda x: x['amount'] > 0, translations + reviews)
    result = sorted(result, key=lambda x: x['start'])

    for item in result:
        item['type'] = item['action']
        item['action'] = PaidTask.get_task_type_title(item['action'])

    for item in result:
        item['start'] = item['start'].strftime('%Y-%m-%d')
        item['end'] = item['end'].strftime('%Y-%m-%d')

    return result


def users(request):
    User = get_user_model()
    json = list(
        User.objects.hide_meta()
                    .select_related('evernote_account')
                    .values('id', 'username', 'full_name')
    )
    response = jsonify(json)

    return HttpResponse(response, content_type="application/json")
