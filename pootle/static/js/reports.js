(function ($) {

  window.PTL = window.PTL || {};

  PTL.reports = {

    init: function () {

      /* Compile templates */
      this.tmpl = {
        results: _.template($('#language_user_activity').html()),
        summary: PTL.reports.freeUserReport ? '' : _.template($('#summary').html()),
        paid_tasks: PTL.reports.freeUserReport ? '' : _.template($('#paid-tasks').html()),
      };

      $(window).resize(function() {
        PTL.reports.drawChart();
      });

      if (PTL.reports.adminReport) {
        $(document).on('change', '#reports-user', function (e) {
          PTL.reports.userName = $('#reports-user').val();
          PTL.reports.update();
        });
        $(document).on('click', '#user-rates-form input.submit', this.updateRates);
        $(document).on('click', '#reports-paid-tasks .js-remove-task', this.removePaidTask);
        $('#reports-user').select2({'data': PTL.reports.users});
      } else {
        $('#reports-form').empty();
      }

      $(document).on('click', '#paid-task-form input.submit', this.addPaidTask);
      $(document).on('change', '#id_currency', this.refreshCurrency);
      $(document).on('change', '#id_task_type', this.onPaidTaskTypeChange);

      var taskType = $('#id_task_type').val();
      this.refreshAmountMeasureUnits(taskType);

      this.currentRowIsEven = false;

      $.history.init(function (hash) {
        var params = PTL.utils.getParsedHash(hash);

        // Walk through known report criterias and apply them to the
        // reports object
        if ('month' in params) {
          PTL.reports.month = moment(params.month);
        } else {
          PTL.reports.month = moment(PTL.reports.serverTime);
        }
        if ('username' in params) {
          PTL.reports.userName = params.username;
        }
        PTL.reports.updateMonthSelector();
        $('#reports-user').select2('val', PTL.reports.userName);

        if (!PTL.reports.compareParams(params)) {
          PTL.reports.buildResults();
        }

        PTL.reports.loadedHashParams = params;
        $('#detailed a').attr('href', PTL.reports.detailedUrl + '?' + PTL.utils.getHash());
      }, {'unescape': true});

    },

    updateRates: function () {
      var reqData = $('#user-rates-form').serializeObject();

      $.ajax({
        url: PTL.reports.updateUserRatesUrl,
        type: 'POST',
        data: reqData,
        dataType: 'json',
        success: function (data) {
          if (data.scorelog_count + data.paid_task_count > 0) {
            PTL.reports.buildResults();
          }
        },
        error: function (xhr, s) {
          alert('Error status: ' + xhr.status);
        }
      });
      return false;
    },

    addPaidTask: function () {
      var reqData = $('#paid-task-form').serializeObject();

      $.ajax({
        url: PTL.reports.addPaidTaskUrl,
        type: 'POST',
        data: reqData,
        dataType: 'json',
        success: function (data) {
          if (data.result > 0) {
            $('#id_amount').val(0);
            $('#id_description').val('');
            PTL.reports.buildResults();
          }
        },
        error: function (xhr, s) {
          alert('Error status: ' + xhr.status);
        }
      });
      return false;
    },

    removePaidTask: function () {
      $.ajax({
        url: PTL.reports.removePaidTaskUrl + $(this).data('id'),
        type: 'DELETE',
        dataType: 'json',
        success: function (data) {
          PTL.reports.buildResults();
        },
        error: function (xhr, s) {
          alert('Error status: ' + xhr.status);
        }
      });
      return false;
    },

    refreshCurrency: function (e) {
      var currency = $(this).val();
      $('#user-rates-form .currency').text(currency);
    },

    onPaidTaskTypeChange: function (e) {
      var taskType = $(this).val();

      PTL.reports.refreshAmountMeasureUnits(taskType);
      $('#id_paid_task_rate').val(PTL.reports.getRateByTaskType(taskType));
    },

    refreshAmountMeasureUnits: function (taskType) {
      $('#paid-task-form .units').hide();
      $('#paid-task-form .units.task-' + taskType).show();
    },

    getRateByTaskType: function (taskType) {
      return {
        0: PTL.reports.user.rate,
        1: PTL.reports.user.review_rate,
        2: PTL.reports.user.hourly_rate,
      }[taskType] || 0;
    },

    validate: function () {
      if (PTL.reports.userName) {
        return moment(PTL.reports.month).date() == 1;
      }
      return false;
    },

    update: function () {
      if (PTL.reports.validate()) {
        var newHash = $.param({
          'username': PTL.reports.userName,
          'month': PTL.reports.month.format('YYYY-MM'),
        });
        $.history.load(newHash);
      } else {
        alert('Wrong input data');
      }
    },

    compareParams: function (params) {
      var result = true;

      if (PTL.reports.loadedHashParams) {
        for (var p in params) {
          result &= params[p] == PTL.reports.loadedHashParams[p];
        }
      } else {
        result = false;
      }

      return result;
    },

    drawChart: function () {
      $.plot($("#daily-chart"),
        PTL.reports.dailyData.data,
        {
          series: {
            stack: true,
            lines: {show: false, steps: false },
            bars: {
              show: true,
              barWidth: 1000*60*60*24,
              align: "center"
            },
          },
          xaxis: {
              min: parseInt(PTL.reports.dailyData.min_ts) - 1000*60*60*12,
              max: parseInt(PTL.reports.dailyData.max_ts) - 1000*60*60*12,
              minTickSize: [1, "day"],
              mode: "time",
              timeformat: "%b %d, %a",
          },
          yaxis: {
              max: PTL.reports.dailyData.max_day_score
          }
        }
      );
    },

    getPaidTaskSummaryItem: function (type, rate) {
      if (PTL.reports.paid_task_summary) {
        for (var index in PTL.reports.paid_task_summary) {
          if (PTL.reports.paid_task_summary[index].rate === rate &&
              PTL.reports.paid_task_summary[index].type === type) {
            return item
          }
        }
      }

      return null;
    },

    setData: function (data) {
      PTL.reports.data = data;
      data.paid_task_summary = [];
      for (var index in data.paid_tasks) {
        var task = data.paid_tasks[index],
            item = PTL.reports.getPaidTaskSummaryItem(task.type, task.rate);
        if (item !== null) {
          item.amount += task.amount
        } else {
          PTL.reports.data.paid_task_summary.push({
            'type': task.type,
            'amount': task.amount,
            'action': task.action,
            'rate': task.rate,
          });
        }
      }
    },

    buildResults: function () {
      var reqData = {
        month: PTL.reports.month.format('YYYY-MM'),
        username: PTL.reports.userName
      };

      $('body').spin();
      $.ajax({
        url: 'activity',
        data: reqData,
        dataType: 'json',
        async: true,
        success: function (data) {
          PTL.reports.serverTime = data.meta.now;
          PTL.reports.now = moment(data.meta.now);
          PTL.reports.month = moment(data.meta.month);

          $('#reports-results').empty();
          $('#reports-results').html(PTL.reports.tmpl.results(data)).show();
          $("#js-breadcrumb-user").html(data.meta.user.formatted_name).show();
          var showChart = data.daily !== undefined && data.daily.nonempty;
          $('#reports-activity').toggle(showChart);
          if (showChart) {
            PTL.reports.dailyData = data.daily;
            PTL.reports.drawChart();
          }
          PTL.reports.setData(data);
          if (!PTL.reports.freeUserReport) {
            $('#reports-paid-tasks').html(PTL.reports.tmpl.paid_tasks(PTL.reports.data));
            $('#reports-summary').html(PTL.reports.tmpl.summary(PTL.reports.data));
          }
          if (data.meta.user) {
            PTL.reports.user = data.meta.user;
            PTL.reports.updateMonthSelector();
            PTL.reports.setPaidTaskDate();

            $('#reports-params').show();
            $('#detailed').show();

            $('#id_username').val(PTL.reports.user.username);
            $('#id_user').val(PTL.reports.user.id);
            $('#id_rate').val(PTL.reports.user.rate);
            $('#id_review_rate').val(PTL.reports.user.review_rate);
            $('#id_hourly_rate').val(PTL.reports.user.hourly_rate);

            var taskType = $('#id_task_type').val();
            $('#id_paid_task_rate').val(PTL.reports.getRateByTaskType(taskType));

            if (PTL.reports.user.currency) {
              $('#id_currency').val(PTL.reports.user.currency);
            }
            $('#user-rates-form .currency').text($('#id_currency').val())
            $('#forms').show();
          } else {
            $('#forms').hide();
          }
          $('body').spin(false);
        },
        error: function (xhr, s) {
          alert('Error status: ' + $.parseJSON(xhr.responseText));
          $('body').spin(false);
        }
      });
    },

    dateRangeString: function (d1, d2, showYear) {
      var res = '',
          m1 = moment(d1),
          m2 = moment(d2);

      showYear = showYear || true;

      if (m1.year() == m2.year()) {
        if (m1.month() == m2.month()) {
          if (m1.date() == m2.date()) {
            return m1.format(showYear ? 'MMMM D, YYYY' : 'MMMM D');
          } else {
            return [
              m1.format('MMMM D'),
              ' &mdash; ',
              m2.date(),
              showYear ? m2.format(', YYYY') : ''
            ].join('');
          }
        } else {
          return [
            m1.format('MMMM D'),
            ' &mdash; ',
            m2.format(showYear ? 'MMMM D, YYYY' : 'MMMM D')
          ].join('');
        }
      } else {
        return [
          m1.format('MMMM D, YYYY'),
          ' &mdash; ',
          m2.format('MMMM D, YYYY')
        ].join('');
      }
    },

    formatDate: function (d) {
      var m = moment(d);
      return m.format('MMM, D');
    },

    cycleEvenOdd: function () {
      PTL.reports.currentRowIsEven = !PTL.reports.currentRowIsEven;

      if (PTL.reports.currentRowIsEven) {
        return 'even';
      } else {
        return 'odd';
      }
    },

    resetRowStyle: function () {
      PTL.reports.currentRowIsEven = false;
    },

    updateMonthSelector: function () {
      $('.js-month').each(function () {
        var $el = $(this),
            link = PTL.reports.adminReport ? '#username=' + PTL.reports.userName + '&' : '#';

        if ($el.hasClass('js-previous')) {
          link += 'month=' + PTL.reports.month.clone().subtract({M:1}).format('YYYY-MM');
        }
        if ($el.hasClass('js-next')){
          link += 'month=' + PTL.reports.month.clone().add({M:1}).format('YYYY-MM');
        }
        $el.attr('href', link);
      });
      $('.dates .selected').html(PTL.reports.month.format('MMMM, YYYY'));
    },

    setPaidTaskDate: function () {
      $('#paid-task-form .month').html(PTL.reports.month.format('MMMM, YYYY'));
      // set paid task date
      if (PTL.reports.now >= PTL.reports.month.clone().add({M: 1})) {
        $('#paid-task-form #id_date').val(PTL.reports.month.clone().add({M: 1}).subtract({d: 1}).format('YYYY-MM-DD'));
      } else if (PTL.reports.now <= PTL.reports.month) {
        $('#paid-task-form #id_date').val(PTL.reports.month.format('YYYY-MM-DD'));
      } else {
        $('#paid-task-form #id_date').val(PTL.reports.now.format('YYYY-MM-DD'));
      }
    },

  };

})(jQuery);

$(function ($) {
  PTL.reports.init();
});
