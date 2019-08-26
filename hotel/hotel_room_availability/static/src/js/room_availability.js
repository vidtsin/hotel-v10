odoo.define('hotel.room_availability', function(require) {
    "use strict";

    var core = require('web.core');
    var data = require('web.data');
    var form_common = require('web.form_common');
    var formats = require('web.formats');
    var Model = require('web.DataModel');
    var time = require('web.time');
    var utils = require('web.utils');

    var QWeb = core.qweb;
    var _t = core._t;

    var RoomAvailability = form_common.FormWidget.extend(form_common.ReinitializeWidgetMixin, {
        events: {
            "click .oe_room_availability_weekly a": "go_to",
        },
        ignore_fields: function() {
            return [];
        },
        init: function() {

            this._super.apply(this, arguments);
            this.set({
                sheets: {},
                room_sheet: {},
                line_sheet: {},
                date_from: false,
                date_to: false,
                company_id: false,
                room_id: {},
                hotel: {},
                id: 0
            });
            this.rec = this.field_manager.get_fields_values()
            this.set({
                "id": this.rec.id
            });
            this.field_manager.on("field_changed:room_availability_ids", this, this.query_sheets);
            this.field_manager.on("field_changed:date_from", this, function() {
                this.set({
                    "date_from": time.str_to_date(this.field_manager.get_field_value("date_from"))
                });
            });
            this.field_manager.on("field_changed:date_to", this, function() {
                this.set({
                    "date_to": time.str_to_date(this.field_manager.get_field_value("date_to"))
                });
            });
            this.field_manager.on("field_changed:rooms_ids", this, function() {
                var room_ids = this.field_manager.get_field_value("rooms_ids")
                if (room_ids[0]) {
                    this.set({
                        "room_id": room_ids[0][2]
                    });
                }
                this.sheet_query();
            });
            this.field_manager.on("field_changed:company_id", this, function() {
                this.set({
                    "company_id": this.field_manager.get_field_value("company_id")
                });
                this.set({
                    room_sheet: {}
                });
                this.set({
                    sheets: {}
                });
                this.sheet_query();
            });

            this.on("change:sheets", this, this.update_sheets);
            this.res_o2m_drop = new utils.DropMisordered();
            this.render_drop = new utils.DropMisordered();
            this.description_line = _t("/");
            this.set({
                room_sheet: {}
            });
            this.set({
                sheets: {}
            });
            this.set({
                room_id: []
            })
            this.sheet_query();
        },
        go_to: function(event) {
            var id = JSON.parse($(event.target).data("id"));
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: "hotel.room",
                res_id: id,
                views: [
                    [false, 'form']
                ],
            });
        },
        go_to_register: function(event) {
            var id = JSON.parse($(event.target).data("id"));
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: "hotel.room",
                res_id: id,
                views: [
                    [false, 'form']
                ],
            });
        },
        query_sheets: function() {
            if (this.updating) {
                return;
            }
            this.querying = true;
            var commands = this.field_manager.get_field_value("room_availability_ids");
            var self = this;
            this.res_o2m_drop.add(new Model(this.view.model).call("resolve_2many_commands", ["room_availability_ids", commands, [], new data.CompoundContext()]))
                .done(function(result) {
                    self.querying = false;
                });
        },
        sheet_query: function() {
            var self = this
            var rec = this.field_manager.get_fields_values()
            this.set({
                'id': rec.id
            })
            new Model("hotel.room").call("search_read", [
                [
                    ['active', '=', 'True'],
                    ['id', 'in', this.get('room_id')]
                ],
            ]).then(function(result) {
                self.set({
                    room_sheet: result
                });
                self.set({
                    sheets: result
                });
                if (result.length > 0) {
                    if (self.get('company_id')) {
                        new Model("room.availability.line").call("search_read", [
                                [
                                    ['room_availability_id', 'in', [self.get("id")]]
                                ]
                            ])
                            .then(function(result_1) {
                                self.set({
                                    line_sheet: result_1
                                });
                                if (result_1.length > 0) {
                                    self.set({
                                        sheets: result_1
                                    })
                                }
                            })
                    }
                }
            })
        },
        update_sheets: function() {
            if (this.querying) {
                return;
            }
            this.updating = true;
            var commands = [form_common.commands.delete_all()];
            _.each(this.get("sheets"), function(_data) {
                var data = _.clone(_data);
                if (data.id && data.room_category_id) {
                    commands.push(form_common.commands.link_to(data.id));
                    commands.push(form_common.commands.update(data.id, data));
                } else if (!data.id) {
                    commands.push(form_common.commands.create(data));
                }
            });
            var self = this;
            this.field_manager.set_values({
                'room_availability_ids': commands
            }).done(function() {
                self.updating = false;
            });
        },
        initialize_field: function() {
            form_common.ReinitializeWidgetMixin.initialize_field.call(this);
            this.on("change:sheets", this, this.initialize_content);
            this.on("change:date_to", this, this.initialize_content);
            this.on("change:date_from", this, this.initialize_content);
            this.on("change:company_id", this, this.initialize_content);
        },
        initialize_content: function() {
            if (this.setting) {
                return;
            }
            // don't render anything until we have date_to and date_from
            this.rec = this.field_manager.get_fields_values()
            if (!this.get("date_to") || !this.get("date_from")) {
                return;
            }

            // var rec = this.field_manager.get_fields_values()
            if (this.rec && this.rec.id != false) {
                this.set({
                    "id": this.rec.id
                });
            }
            // it's important to use those vars to avoid race conditions
            var dates;
            var default_get;
            var rooms_types;
            var rooms_types_names;
            // var room_qty = 0;
            var self = this;
            return this.render_drop.add(new Model("room.availability.line").call("default_get", [
                ['room_category_id', 'date', 'room_qty', 'company_id'],
                new data.CompoundContext({
                    'room_category_id': self.get('room_category_id')
                })
            ]).then(function(result) {
                default_get = result;
                dates = [];
                var booked_rooms = [];
                var start = self.get("date_from");
                var end = self.get("date_to");
                while (start <= end) {
                    dates.push(start);
                    var m_start = moment(start).add(1, 'days');
                    start = m_start.toDate();
                }
                // group by room category
                if (self.get("hotel").length > 0) {
                    var hotel = self.get("hotel")[0]
                } else {
                    var hotel = self.get("hotel")
                }
                var sheet = self.get("line_sheet")
                rooms_types = self.get("room_sheet")

                var rooms_types_names = {}
                _.each(rooms_types, function(el) {
                    rooms_types_names[el.id] = el.name;
                })

                self.dates = dates;
                self.rooms_types = rooms_types;
                self.rooms_types_names = rooms_types_names;
                self.default_get = default_get;
                //real rendering
                self.display_data();
                // we need the name_get of the projects
                return new Model("hotel.room").call("name_get", [_.pluck(rooms_types, "id"), ]).then(function(result) {
                    rooms_types_names = {};
                    _.each(result, function(el) {
                        rooms_types_names[el[0]] = el[1];
                    });
                    rooms_types = _.sortBy(rooms_types, function(el) {
                        return rooms_types[el.id];
                    });
                });
            }));
        },
        get_room_data: function(room_id) {
            var self = this;
            var name_row = document.getElementById("room_name-" + room_id);
            var closed_tr = document.getElementById("closed_tr-" + room_id);
            var booked_tr = document.getElementById("booked_tr-" + room_id);
            var avail_room_tr = document.getElementById("avail_room_tr-" + room_id);
            if (!$(name_row).hasClass('rendered')) {
                var day_count = 0;
                var sheet = self.get("sheets");
                var start = self.get("date_from");
                var end = self.get("date_to");
                new Model("hotel_reservation.line").call("get_room_value_from_daterange", [
                    sheet[0], room_id, moment(start).format('YYYY-MM-DD'), moment(end).format('YYYY-MM-DD')
                ]).then(function(result) {
                    _.each(self.dates, function(date) {
                        var room_data = _.find(result, function(data) {
                            return data.date == moment(date).format('YYYY-MM-DD');
                        });
                        if (typeof room_data !== "undefined") {
                            // First Row
                            var name_cell = name_row.insertCell();
                            var cell = '';
                            if (self.get('effective_readonly')) {
                                cell = '<span class="oe_timesheet_weekly_box oe_timesheet_weekly_input" data-day-count="' + day_count + '" data-room="' + room_id + '">' +  room_data.total_qty + '</span>'
                            } else {
                                cell = '<input class="oe_timesheet_weekly_input" pattern="[0-9]" type="text" data-day-count="' + day_count + '" data-room="' + room_id + '" value="' + room_data.total_qty + '">';
                            }
                            name_cell.innerHTML = cell;
                            $(name_cell).addClass('input_td')

                            // Second Row
                            var closed_cell = closed_tr.insertCell();
                            var closed_cell_data = '';
                            var checked = room_data.closed;
                            if (self.get('effective_readonly')) {
                                if (checked) {
                                    closed_cell_data = '<input class="close_checkbox" disabled="" data-origin="' + checked + '" checked="' + checked + '" type="checkbox" data-day-count="' + day_count + '" data-room="' + room_id + '"/>'
                                } else {
                                    closed_cell_data = '<input class="close_checkbox" disabled="" type="checkbox" data-origin="' + checked + '" data-day-count="' + day_count + '" data-room="' + room_id + '"/>'
                                }
                            } else {
                                if (checked) {
                                    closed_cell_data = '<input class="close_checkbox" checked="' + checked + '" type="checkbox" data-origin="' + checked + '" data-day-count="' + day_count + '" data-room="' + room_id + '"/>'
                                } else {
                                    closed_cell_data = '<input class="close_checkbox" type="checkbox" data-day-count="' + day_count + '" data-origin="' + checked + '" data-room="' + room_id + '"/>'
                                }
                            }
                            closed_cell.innerHTML = closed_cell_data;

                            // Third row
                            var booked_cell = booked_tr.insertCell();
                            var booked_cell_data = '';
                            booked_cell_data = '<span class="booked_rooms" data-day-count="' + day_count + '" data-room="' + room_id + '">' + room_data.booked + '</span>'
                            booked_cell.innerHTML = booked_cell_data;
                            $(booked_cell).addClass('pricelist_td')


                            // Fourth row
                            var avail_room_cell = avail_room_tr.insertCell();
                            var avail_cell_data = '';
                            avail_cell_data = '<span class="avail_rooms" data-day-count="' + day_count + '" data-room="' + room_id + '">' + room_data.avail + '</span>'
                            avail_room_cell.innerHTML = avail_cell_data;
                            if (room_data.avail > 0) {
                                $(avail_room_cell).addClass('bg-success')
                            } else {
                                $(avail_room_cell).addClass('bg-danger')
                            }


                            self.style_checkbox(day_count, room_id)
                            day_count++;
                        }
                    });
                    var total_qty_cell = name_row.insertCell();
                    $(total_qty_cell).addClass('total_qty_cell bg-default');
                    $(total_qty_cell).attr('data-room', room_id);
                    self.display_total_qty(room_id)

                    var total_checked_cell = closed_tr.insertCell();
                    $(total_checked_cell).addClass('total_checked_cell bg-default');

                    var total_booked_cell = booked_tr.insertCell();
                    $(total_booked_cell).addClass('total_booked_cell bg-default');
                    $(total_booked_cell).attr('data-room', room_id);
                    self.display_booked_qty(room_id)

                    var total_avail_cell = avail_room_tr.insertCell();
                    $(total_avail_cell).addClass('total_avail_cell bg-default');
                    $(total_avail_cell).attr('data-room', room_id);
                    self.display_avail_qty(room_id)
                    self.style_caption(room_id, $(total_qty_cell).outerHeight(), $(total_checked_cell).outerHeight(), $(total_booked_cell).outerHeight(), $(total_avail_cell).outerHeight());
                });

                if (!self.get('effective_readonly')) {
                    $(document).on('change', '.close_checkbox', function(event) {
                        event.preventDefault();
                        var room_qty = $('.oe_timesheet_weekly_input[data-room="' + $(this).data('room') + '"][data-day-count="' + $(this).data('day-count') + '"]');
                        self.style_checkbox($(this).data('day-count'), $(this).data('room'));
                        if ($(this).data('origin') !== $(this).prop('checked') && !room_qty.hasClass('value_changed')) {
                            $(this).addClass('value_changed');
                        } else {
                            $(this).removeClass('value_changed');
                        }
                        self.set_o2m_values();
                    });
                    $(document).on('change', '.oe_timesheet_weekly_input', function(event) {
                        event.preventDefault();
                        var close = $('.close_checkbox[data-room="' + $(this).data('room') + '"][data-day-count="' + $(this).data('day-count') + '"]');
                        if ($(this).data('origin') != $(this).val() && !close.hasClass('value_changed')) {
                            $(this).addClass('value_changed');
                        } else {
                            $(this).removeClass('value_changed');
                        }
                        self.set_o2m_values();
                        self.display_total_qty($(this).data('room'));
                        self.display_booked_qty($(this).data('room'));
                        self.display_avail_qty($(this).data('room'));
                        var booked = $('.booked_rooms[data-room="' + $(this).data('room') + '"][data-day-count="' + $(this).data('day-count') + '"]').text();
                        var avail = parseInt($(this).val()) - parseInt(booked)
                        $('.avail_rooms[data-room="' + $(this).data('room') + '"][data-day-count="' + $(this).data('day-count') + '"]').text(avail)
                    });
                }
                $(name_row).addClass('rendered');
            }
        },
        set_o2m_values: function() {
            var self = this;
            this.setting = true;
            var ops = [];
            var commands = [form_common.commands.delete_all()];
            _.each(self.rec.room_availability_ids, function(_data) {
                var data = _.clone(_data);
                if (typeof data[1] !== undefined) {
                    commands.push(form_common.commands.link_to(data[1]));
                    commands.push(form_common.commands.update(data[1], data[2]));
                }
            });
            _.each($(".value_changed"), function(input) {
                var day_count = $(input).data('day-count');
                var room_id = $(input).data('room');
                var room_qty = $('.oe_timesheet_weekly_input[data-room="' + room_id + '"][data-day-count="' + day_count + '"]').val();
                var close = $('.close_checkbox[data-room="' + room_id + '"][data-day-count="' + day_count + '"]').prop('checked');
                var rec_date = $('#dom_date_head-' + day_count).data('date');
                var room_data = _.find(self.rooms_types, function(data) {
                    return data.id == room_id;
                });
                if (self.get('line_sheet') !== undefined) {
                    var prev_id = _.find(self.get('line_sheet'), function(data) {
                        return data.room_category_id[0] == room_id && data.date == time.date_to_str(new Date(rec_date));
                    });
                    if (prev_id !== undefined) {
                        if (prev_id.id !== undefined) {
                            commands.push(form_common.commands.delete(prev_id.id));
                        }
                    }
                }
                var values = {
                    room_qty: parseInt(room_qty),
                    room_category_id: parseInt(room_id),
                    room_availability_id: self.rec.id,
                    date: time.date_to_str(new Date(rec_date)),
                    close: close,
                    room_cost_price: room_data.price
                }
                var data = _.clone(values);
                commands.push(form_common.commands.create(data));
            });
            this.field_manager.set_values({
                'room_availability_ids': commands
            })
            this.setting = false;
        },
        display_total_qty: function(room_id) {
            var self = this;
            var total = 0;
            if (self.get('effective_readonly')) {
                _.each($(".oe_timesheet_weekly_input[data-room='" + room_id + "']"), function(input) {
                    total += parseInt($(input).text());
                });
            } else {
                _.each($(".oe_timesheet_weekly_input[data-room='" + room_id + "']"), function(input) {
                    total += parseInt($(input).val());
                });
            }
            $(".total_qty_cell[data-room='" + room_id + "']").html(total);
        },
        display_booked_qty: function(room_id) {
            var total = 0;
            _.each($(".booked_rooms[data-room='" + room_id + "']"), function(input) {
                total += parseInt($(input).text());
            });
            $(".total_booked_cell[data-room='" + room_id + "']").html(total);
        },
        display_avail_qty: function(room_id) {
            var total = 0;
            _.each($(".avail_rooms[data-room='" + room_id + "']"), function(input) {
                total += parseInt($(input).text());
            });
            $(".total_avail_cell[data-room='" + room_id + "']").html(total);
        },
        style_caption: function(room_id, name_height, check_height, booked_height, avail_height) {
            var name_row = $("#room_caption-" + room_id);
            var closed_tr = $("#closed_caption-" + room_id);
            var booked_tr = $("#booked_caption-" + room_id);
            var avail_room_tr = $("#avail_caption-" + room_id);
            $('head').append("<style>#room_name-" + room_id + "::before{ content:'Room'; overflow: hidden; text-overflow: ellipsis; width: " + (name_row.outerWidth() + (name_row.next().outerWidth() * 2)) + "px !important; height: " + name_height + "px !important; }</style>");
            $('head').append("<style>#closed_tr-" + room_id + "::before{ content:'Closed'; overflow: hidden; text-overflow: ellipsis; width: " + (closed_tr.outerWidth() + (closed_tr.next().outerWidth() * 2)) + "px !important; height: " + check_height + "px !important; padding: 0.75rem; }</style>");
            $('head').append("<style>#booked_tr-" + room_id + "::before{ content:'Booked'; overflow: hidden; text-overflow: ellipsis; width: " + (booked_tr.outerWidth() + (booked_tr.next().outerWidth() * 2)) + "px !important; height: " + booked_height + "px !important; padding: 0.75rem; }</style>");
            $('head').append("<style>#avail_room_tr-" + room_id + "::before{ content:'Available'; overflow: hidden; text-overflow: ellipsis; width: " + (avail_room_tr.outerWidth() + (avail_room_tr.next().outerWidth() * 2)) + "px !important; height: " + avail_height + "px !important; padding: 0.75rem; }</style>");
        },
        style_checkbox: function(day_count, room_id) {
            var input = $('.oe_timesheet_weekly_input[data-room="' + room_id + '"][data-day-count="' + day_count + '"]').parent();
            var booked = $('.booked_rooms[data-room="' + room_id + '"][data-day-count="' + day_count + '"]').parent();
            var available = $('.avail_rooms[data-room="' + room_id + '"][data-day-count="' + day_count + '"]').parent();
            var checked = $('.close_checkbox[data-room="' + room_id + '"][data-day-count="' + day_count + '"]').prop('checked');
            if (checked) {
                $('.close_checkbox[data-room="' + room_id + '"][data-day-count="' + day_count + '"]').parent().css({
                    "background-color": "grey",
                    "color": "white"
                });
                $(input).css({
                    "background-color": "grey",
                });
                $(booked).css({
                    "background-color": "grey",
                    "color": "white"
                });
                $(available).css({
                    "background-color": "grey",
                    "color": "white"
                });
            } else {
                $('.close_checkbox[data-room="' + room_id + '"][data-day-count="' + day_count + '"]').parent().removeAttr("style");
                $(input).removeAttr("style");
                $(booked).removeAttr("style");
                $(available).removeAttr("style");
            }
        },
        destroy_content: function() {
            if (this.dfm) {
                this.dfm.destroy();
                this.dfm = undefined;
            }
        },
        is_valid_value: function(value) {
            this.view.do_notify_change();
            var split_value = value.split(":");
            var valid_value = true;
            if (split_value.length > 2) {
                return false;
            }
            _.detect(split_value, function(num) {
                if (isNaN(num)) {
                    valid_value = false;
                }
            });
            return valid_value;
        },
        display_data: function() {
            var self = this;
            self.$el.html(QWeb.render("hotel_room_availability.RoomAvailability", {
                widget: self
            }));
            self.set_tr_width();
            $(document).on('click', '.accordian_btn', function(event) {
                if ($(this).hasClass('collapsed')) {
                    $(this).removeClass('expanded_row').addClass('closed_row');
                } else if (!$(this).hasClass('collapsed')) {
                    $(this).removeClass('closed_row').addClass('expanded_row');
                    self.get_room_data($(this).data('room'));
                }
            })
        },
        get_box: function(rooms_type, day_count) {
            return this.$('.oe_timesheet_weekly_input[data-room="' + rooms_type.product_id + '"][data-day-count="' + day_count + '"]');
        },
        set_avail_box: function(rooms_type, day_count, show_value_in_hour) {
            var self = this;
            var total_rooms = self.sum_box(rooms_type, day_count, true)
            var booked_rooms = $('.booked_rooms[data-room="' + rooms_type.product_id + '"][data-day-count="' + day_count + '"]').text();
            var avail = parseInt(total_rooms) - parseInt(booked_rooms);
            avail = (show_value_in_hour && avail !== 0) ? this.format_client(avail) : avail
            self.get_available(rooms_type.product_id, day_count).text(avail)
        },
        sum_box: function(rooms_type, day_count, show_value_in_hour) {
            var line_total = 0;
            var sheet = this.get("line_sheet")
            _.each(rooms_type.days[day_count].lines, function(line) {
                if (sheet.length > 0) {
                    for (var i = 0; i < sheet.length; i++) {
                        var sheets = sheet[i]
                        var line_date = new Date(line.date)
                        line_date.setHours(0, 0, 0, 0);
                        var sheet_date = new Date(sheets.date)
                        sheet_date.setHours(0, 0, 0, 0);
                        if (line_date.getTime() == sheet_date.getTime() && sheets.room_category_id[0] == line.room_category_id &&
                            line.company_id == sheets.company_id[0] && sheets.room_qty > 0) {
                            line_total = sheets.room_qty;
                            break;
                        } else {
                            line_total = line.room_qty;
                        }
                    }
                } else {
                    line_total = line.room_qty;
                }
            });
            return (show_value_in_hour && line_total !== 0) ? this.format_client(line_total) : line_total;
        },
        get_checkbox: function(rooms_type, day_count) {
            return this.$('.close_checkbox[data-room="' + rooms_type.product_id + '"][data-day-count="' + day_count + '"]');
        },
        get_available: function(room, day_count) {
            return this.$('.avail_rooms[data-room="' + room + '"][data-day-count="' + day_count + '"]');
        },
        checkbox_value: function(rooms_type, day_count, show_value_in_hour) {
            var checked = false;
            var sheet = this.get("line_sheet")
            _.each(rooms_type.days[day_count].lines, function(line) {
                if (sheet.length > 0) {
                    for (var i = 0; i < sheet.length; i++) {
                        var sheets = sheet[i]
                        var line_date = new Date(line.date)
                        line_date.setHours(0, 0, 0, 0);
                        var sheet_date = new Date(sheets.date)
                        sheet_date.setHours(0, 0, 0, 0);
                        if (line_date.getTime() == sheet_date.getTime() && sheets.room_category_id[0] == line.room_category_id &&
                            line.company_id == sheets.company_id[0] && sheets.room_qty > 0) {
                            checked = sheets.close;
                            break;
                        } else {
                            checked = line.close;
                        }
                    }
                } else {
                    checked = line.close;
                }
            });
            return checked;
        },

        checked_box_style: function(room, day_count, checked) {
            var input = $('.oe_timesheet_weekly_input[data-room="' + room + '"][data-day-count="' + day_count + '"]').parent();
            var booked = $('.booked_rooms[data-room="' + room + '"][data-day-count="' + day_count + '"]').parent();
            var available = $('.avail_rooms[data-room="' + room + '"][data-day-count="' + day_count + '"]').parent();
            if (checked) {
                $('.close_checkbox[data-room="' + room + '"][data-day-count="' + day_count + '"]').parent().css({
                    "background-color": "grey",
                    "color": "white"
                });
                $(input).css({
                    "background-color": "grey",
                    "color": "white"
                });
                $(booked).css({
                    "background-color": "grey",
                    "color": "white"
                });
                $(available).css({
                    "background-color": "grey",
                    "color": "white"
                });
            } else {
                $('.close_checkbox[data-room="' + room + '"][data-day-count="' + day_count + '"]').parent().removeAttr("style");
                $(input).removeAttr("style");
                $(booked).removeAttr("style");
                $(available).removeAttr("style");
            }
        },

        available_style: function(room, day_count, value) {
            var box = this.get_available(room, day_count)
            if (value <= 0) {
                $(box).parent().css('background-color', '#f2dede');
            } else {
                $(box).parent().css('background-color', '#dff0d8');
            }
        },
        set_tr_width: function() {
            var width = $(".oe_timesheet_weekly_account").outerWidth();
            $('head').append("<style>.value-tr::before{ content:'bar'; width: " + width + "px !important; }</style>");
            $('head').append("<style>.input-tr::before{ content:'bar'; width: " + width + "px !important; }</style>");
        },
        display_totals: function() {
            var self = this;
            var day_tots = _.map(_.range(self.dates.length), function() {
                return 0;
            });
            var super_tot = 0;
            _.each(self.rooms_types, function(room) {
                var acc_tot = 0;
                _.each(_.range(self.dates.length), function(day_count) {
                    var sum = self.sum_box(room, day_count);
                    acc_tot += sum;
                    day_tots[day_count] += sum;
                    super_tot += sum;
                });
                self.$('[data-room-total="' + room.product_id + '"]').html(self.format_client(acc_tot));
            });
            _.each(_.range(self.dates.length), function(day_count) {
                self.$('[data-day-total="' + day_count + '"]').html(self.format_client(day_tots[day_count]));
            });
            this.$('.oe_timesheet_weekly_supertotal').html(self.format_client(super_tot));
        },
        display_avail_totals: function() {
            _.each(this.$('.avail_room_tr'), function(avail_room) {
                var total = 0
                $(avail_room).find('td').each(function() {
                    total += parseInt($(this).text())
                });
                if (!isNaN(total)) {
                    $(avail_room).find('th.avail_total').text(total);
                }
            });
        },
        sync: function() {
            this.setting = true;
            this.set({
                sheets: this.generate_o2m_value()
            });
            this.set({
                line_sheet: this.generate_o2m_value()
            })
            this.setting = false;
        },
        //converts hour value to float
        parse_client: function(value) {
            return formats.parse_value(value, {
                type: "interger"
            });
        },
        //converts float value to hour
        format_client: function(value) {
            return formats.format_value(value, {
                type: "interger"
            });
        },
        generate_o2m_value: function() {
            var ops = [];
            var ignored_fields = this.ignore_fields();
            _.each(this.rooms_types, function(rooms_type) {
                _.each(rooms_type.days, function(day) {
                    _.each(day.lines, function(line) {
                        if (line.room_qty !== 0 && rooms_type.room_qty != line.room_qty || rooms_type.close != line.close) {
                            var tmp = _.clone(line);
                            _.each(line, function(v, k) {
                                if (v instanceof Array) {
                                    tmp[k] = v[0];
                                }
                            });
                            // we remove line_id as the reference to the _inherits field will no longer exists
                            tmp = _.omit(tmp, ignored_fields);
                            ops.push(tmp);
                        }
                    });
                });
            });
            return ops;
        },
    });
    core.form_custom_registry.add('room_availability', RoomAvailability);
});
