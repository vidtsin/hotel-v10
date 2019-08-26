odoo.define('hotel_quick_reservation.quick_reservation', function(require) {
    "use strict";

    var core = require('web.core');
    var Dialog = require('web.Dialog');
    var form_common = require('web.form_common');
    var Widget = require('web.Widget');
    var CalendarView = require('web_calendar.CalendarView');
    var Model = require('web.Model');
    var time = require('web.time');
    var widgets = require('web_calendar.widgets');
    var local_storage = require('web.local_storage');

    var _t = core._t;
    var _lt = core._lt;
    var QWeb = core.qweb;

    function get_fc_defaultOptions() {
        var dateFormat = time.strftime_to_moment_format(_t.database.parameters.date_format);

        // moment.js converts '%p' to 'A' for 'AM/PM'
        // But FullCalendar v1.6.4 supports 'TT' format for 'AM/PM' but not 'A'
        // NB: should be removed when fullcalendar is updated to 2.0 because it would
        // be supported. See the following link
        // http://fullcalendar.io/wiki/Upgrading-to-v2/
        var timeFormat = time.strftime_to_moment_format(_t.database.parameters.time_format).replace('A', 'TT');

        // adapt format for fullcalendar v1.
        // see http://fullcalendar.io/docs1/utilities/formatDate/
        var conversions = [
            ['YYYY', 'yyyy'],
            ['YY', 'yy'],
            ['DDDD', 'dddd'],
            ['DD', 'dd']
        ];
        _.each(conversions, function(conv) {
            dateFormat = dateFormat.replace(conv[0], conv[1]);
        });

        // If 'H' is contained in timeFormat display '10:00'
        // Else display '10 AM'.
        // See : http://fullcalendar.io/docs1/utilities/formatDate/
        var hourFormat = function(timeFormat) {
            if (/H/.test(timeFormat))
                return 'HH:mm';
            return 'hh TT';
        };

        return {
            weekNumberTitle: _t("W"),
            allDayText: _t("All day"),
            monthNames: moment.months(),
            monthNamesShort: moment.monthsShort(),
            dayNames: moment.weekdays(),
            dayNamesShort: moment.weekdaysShort(),
            firstDay: moment()._locale._week.dow,
            weekNumberCalculation: function(date) {
                return moment(date).week();
            },
            axisFormat: hourFormat(timeFormat),
            // Correct timeformat for agendaWeek and agendaDay
            // http://fullcalendar.io/docs1/text/timeFormat/
            timeFormat: timeFormat + ' {- ' + timeFormat + '}',
            weekNumbers: true,
            titleFormat: {
                month: 'MMMM yyyy',
                week: "w",
                day: dateFormat,
            },
            columnFormat: {
                month: 'ddd',
                week: 'ddd ' + dateFormat,
                day: 'dddd ' + dateFormat,
            },
            weekMode: 'liquid',
            snapMinutes: 15,
        };
    }

    CalendarView.include({
        open_event: function(id, title) {
            var self = this;
            var attrs = this.fields_view.arch.attrs;
            if (attrs.reservation_form === 'True') {
                var search_domain = [
                    ['id', '=', id]
                ];
                var result;
                new Model(this.model).call('search_read', [search_domain, []]).then(function(result_set) {
                    var result = result_set[0];
                    var checkin_date = new Date(result.room_date);
                    var day = 60 * 60 * 24 * 1000;
                    var checkout_date =new Date(checkin_date.getTime() + day);
                    new form_common.FormViewDialog(self, {
                        res_model: 'hotel.reservation',
                        context: {
                            default_checkin: checkin_date,
                            default_checkout: checkout_date,
                            default_reservation_line: [
                                [0, 0, {
                                    name: _lt('New'),
                                    room_id: result.room_id[0],
                                    qty: 1,
                                    price_unit: result.price,
                                    checkin: checkin_date,
                                    checkout: checkout_date,
                                }]
                            ]
                        },
                        title: title,
                    }).open();
                })
            } else if (!this.open_popup_action) {
                var index = this.dataset.get_id_index(id);
                this.dataset.index = index;
                if (this.write_right) {
                    this.do_switch_view('form', {
                        mode: "edit"
                    });
                } else {
                    this.do_switch_view('form', {
                        mode: "view"
                    });
                }
            } else {
                var res_id = parseInt(id).toString() === id ? parseInt(id) : id;
                new form_common.FormViewDialog(this, {
                    res_model: this.model,
                    res_id: res_id,
                    context: this.dataset.get_context(),
                    title: title,
                    view_id: +this.open_popup_action,
                    readonly: true,
                    buttons: [{
                            text: _t("Edit"),
                            classes: 'btn-primary',
                            close: true,
                            click: function() {
                                self.dataset.index = self.dataset.get_id_index(id);
                                self.do_switch_view('form', {
                                    mode: "edit"
                                });
                            }
                        },

                        {
                            text: _t("Delete"),
                            close: true,
                            click: function() {
                                self.remove_event(res_id);
                            }
                        },

                        {
                            text: _t("Close"),
                            close: true
                        }
                    ]
                }).open();
            }
            return false;
        },

        style_sidebar: function() {
            var self = this;
            self.sidebar.filter.$el.find('input[type="checkbox"]').each(function(index, el) {
                if ($(this).prop("checked")) {
                    $(this).parent().parent().removeClass('checkbox_uncheck').addClass('checkbox_checked');
                } else {
                    $(this).parent().parent().removeClass('checkbox_checked').addClass('checkbox_uncheck');
                }
            });
            var sidebar = self.$sidebar_container.find('.o_calendar_contacts');
            sidebar.addClass('reservation_view_filters');
        },

        perform_necessary_name_gets: function(evts) {
            var result = this._super(evts);
            var self = this;
            var attrs = this.fields_view.arch.attrs;
            if (attrs.reservation_form === 'True') {
                self.style_sidebar();
            }
            return result;
        },

        init_calendar: function() {
            var self = this;
            var filter_removed = false;
            var attrs = this.fields_view.arch.attrs;
            if (attrs.reservation_form === 'True') {
                var defs = [];
                if (!this.sidebar) {
                    var translate = get_fc_defaultOptions();
                    this.sidebar = new widgets.Sidebar(this);
                    defs.push(this.sidebar.appendTo(this.$sidebar_container));
                    this.$small_calendar = this.$(".o_calendar_mini");
                    this.$small_calendar.datepicker({
                        onSelect: this.calendarMiniChanged(this),
                        dayNamesMin: translate.dayNamesShort,
                        monthNames: translate.monthNamesShort,
                        firstDay: translate.firstDay,
                    });

                    defs.push(this.extraSideBar());

                    // Add show/hide button and possibly hide the sidebar
                    this.$sidebar_container.append($('<i>').addClass('o_calendar_sidebar_toggler fa'));
                    this.toggle_sidebar((local_storage.getItem('web_calendar_full_width') !== 'true'));
                }
                this.$calendar.fullCalendar(this.get_fc_reservation_init_options());

                self.style_sidebar();
                return $.when.apply($, defs);
            } else {
                return this._super();
            }
        },
        /**
         * Get all_filters ordered by label
         */
        get_all_filters_ordered: function() {
            var self = this;
            var attrs = this.fields_view.arch.attrs;
            if (attrs.reservation_form === 'True') {
                if(!self.filter_removed){
                    _.each(this.all_filters, function(filter){
                        filter.is_checked = false;
                    })
                    self.filter_removed = true;
                }
            }
            return _.values(this.all_filters).sort(function(f1,f2) {
                return _.string.naturalCmp(f1.label, f2.label);
            });
        },
        get_fc_reservation_init_options: function() {
            //Documentation here : http://arshaw.com/fullcalendar/docs/
            var self = this;
            return $.extend({}, get_fc_defaultOptions(), {
                defaultView: (this.mode == "month") ? "month" : ((this.mode == "week") ? "agendaWeek" : ((this.mode == "day") ? "agendaDay" : "agendaWeek")),
                header: false,
                selectable: !this.options.read_only_mode && this.create_right,
                selectHelper: true,
                editable: this.editable,
                droppable: true,

                // callbacks
                viewRender: function(view) {
                    var mode = (view.name == "month") ? "month" : ((view.name == "agendaWeek") ? "week" : "day");
                    if (self.$buttons !== undefined) {
                        self.$buttons.find('.active').removeClass('active');
                        self.$buttons.find('.o_calendar_button_' + mode).addClass('active');
                    }

                    var title = self.title + ' (' + ((mode === "week") ? _t("Week ") : "") + view.title + ")";
                    self.set({
                        'title': title
                    });

                    self.$calendar.fullCalendar('option', 'height', Math.max(290, parseInt(self.$('.o_calendar_view').height())));

                    setTimeout(function() {
                        var $fc_view = self.$calendar.find('.fc-view');
                        var width = $fc_view.find('> table').width();
                        $fc_view.find('> div').css('width', (width > $fc_view.width()) ? width : '100%'); // 100% = fullCalendar default
                    }, 0);
                },
                windowResize: function() {
                    self.$calendar.fullCalendar('render');
                },
                eventDrop: function(event, _day_delta, _minute_delta, _all_day, _revertFunc) {
                    var data = self.get_event_data(event);
                    self.proxy('update_record')(event._id, data); // we don't revert the event, but update it.
                },
                eventResize: function(event, _day_delta, _minute_delta, _revertFunc) {
                    var data = self.get_event_data(event);
                    self.proxy('update_record')(event._id, data);
                },
                eventRender: function(event, element, view) {
                    var split_arr = event.title.split('|');
                    var price_arr = split_arr[0].split(":");
                    var avail_arr = split_arr[1].split(":");
                    var html = "<span class='pull-left'>";
                    html += '<b>';
                    html += price_arr[0];
                    html += ":</b>";
                    html += price_arr[1];
                    html += "</span>";
                    html += "<span class='pull-right'>";
                    html += '<b>';
                    html += avail_arr[0];
                    html += ":</b>";
                    html += avail_arr[1];
                    html += "</span>";
                    element.find('.fc-event-title').html(html);
                },
                eventAfterRender: function(event, element, view) {
                    if ((view.name !== 'month') && (((event.end - event.start) / 60000) <= 30)) {
                        //if duration is too small, we see the html code of img
                        var current_title = $(element.find('.fc-event-time')).text();
                        var new_title = current_title.substr(0, current_title.indexOf("<img") > 0 ? current_title.indexOf("<img") : current_title.length);
                        element.find('.fc-event-time').html(new_title);
                    }
                },
                eventClick: function(event) {
                    self.open_event(event._id, event.title);
                },
                select: function(start_date, end_date, all_day, _js_event, _view) {
                    var checkin_date = new Date(start_date);
                    var day = 60 * 60 * 24 * 1000;
                    var checkout_date =new Date(checkin_date.getTime() + day);
                    if (start_date < new Date()) {
                        return false;
                    } else {
                        new form_common.FormViewDialog(this, {
                            res_model: 'hotel.reservation',
                            context: {
                                default_checkin: checkin_date,
                                default_checkout: checkout_date,
                                default_reservation_line: [
                                    [0, 0, {
                                        qty: 1,
                                        checkin: checkin_date,
                                        checkout: checkout_date,
                                    }]
                                ]
                            },
                            title: _lt('Quick Reservation'),
                        }).open();
                    }
                },
                unselectAuto: false,
            });
        },
    });

})
