odoo.define('hotel.room_pricelist', function(require) {
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

    var RoomPricelist = form_common.FormWidget.extend(form_common.ReinitializeWidgetMixin, {
        events: {
            "click .oe_room_pricelist_weekly a": "go_to",
            'change input': '_onFieldChanged',
        },
        ignore_fields: function() {
            return [];
        },

        _onFieldChanged: function(ev) {
            var self = this;
            this.setting = true;
            var dataset = ev.currentTarget.dataset;
            var value = ev.target.value;
            var res_date = dataset.date;
            var res_room_id = parseInt(dataset.room);
            new Model("room.pricelist.line").call("search_read", [
                    [
                        ['room_pricelist_id', 'in', [self.rec.id]],
                        ['date', '=', res_date],
                        ['room_id', '=', res_room_id],
                    ]
                ])
                .then(function(result_1) {
                    // var commands = [form_common.commands.delete_all()];
                    // _.each(self.rec.room_pricelist_ids, function(_data) {
                    //     var data = _.clone(_data);
                    //     if (typeof data[1] !== undefined) {
                    //         commands.push(form_common.commands.link_to(data[1]));
                    //         commands.push(form_common.commands.update(data[1], data[2]));
                    //     }
                    // });
                    var commands = [];
                    var args = {
                        room_price: parseInt(value),
                        room_id: res_room_id,
                        date: res_date,
                        room_pricelist_id: parseInt(self.rec.id),
                    }
                    if (result_1.length > 0) {
                        _.each(result_1, function(prev_id) {
                            commands.push(form_common.commands.delete(prev_id.id));
                        });
                    } else {
                        var data = _.clone(args);
                        var commands = [form_common.commands.create(data)];
                    }
                    self.field_manager.set_values({
                        'room_pricelist_ids': commands
                    });
                    this.setting = false;
                    self.display_rowprice(res_room_id);
                })
                this.setting = false;
        },

        init: function() {
            var self = this;
            this._super.apply(this, arguments);
            this.set({
                sheets: {},
                room_sheet: {},
                line_sheet: {},
                date_from: time.str_to_date(this.field_manager.get_field_value("date_from")),
                date_to: time.str_to_date(this.field_manager.get_field_value("date_to")),
                company_id: false,
                room_id: {},
                hotel: {},
            });
            this.date_from = time.str_to_date(this.field_manager.get_field_value("date_from"))
            this.date_to = time.str_to_date(this.field_manager.get_field_value("date_to"))
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

        initialize_field: function() {
            form_common.ReinitializeWidgetMixin.initialize_field.call(this);
            this.on("change:sheets", this, this.initialize_content);
            this.on("change:date_to", this, this.initialize_content);
            this.on("change:date_from", this, this.initialize_content);
            this.on("change:company_id", this, this.initialize_content);
        },

        display_rowprice: function(room_id) {
            var self = this;
            var total = 0;
            if (self.mode == 'readonly') {
                _.each($(".oe_timesheet_weekly_input[data-room='" + room_id + "']"), function(input) {
                    total += parseInt($(input).text());
                });
            } else {
                _.each($(".oe_timesheet_weekly_input[data-room='" + room_id + "']"), function(input) {
                    total += parseInt($(input).val());
                });
            }
            $(".total_rowprice_cell[data-room='" + room_id + "']").html(total);
        },

        style_caption: function(room_id) {
            var name_row = $("#room_caption-" + room_id);
            $('head').append("<style>#room_name-" + room_id + "::before{ content:'Room'; overflow: hidden; text-overflow: ellipsis; width: " + (name_row.outerWidth() + (name_row.next().outerWidth() * 2)) + "px !important; height: " + name_row.parents().outerHeight() + "px !important; }</style>");
        },

        get_room_data: function(room_id) {
            var self = this;
            var data_row = document.getElementById("room_name-" + room_id);
            if (!$(data_row).hasClass('rendered')) {
                var day_count = 0;
                new Model("hotel_reservation.line").call("get_room_price_from_daterange", [
                    room_id, moment(self.date_from).format('YYYY-MM-DD'), moment(self.date_to).format('YYYY-MM-DD')
                ]).then(function(result) {
                    _.each(self.dates, function(date) {
                        var room_data = _.find(result, function(data) {
                            return data.date == moment(date).format('YYYY-MM-DD');
                        });
                        if (typeof room_data !== "undefined") {
                            // First Row
                            var price_cell = data_row.insertCell();
                            var cell = '';
                            if (self.mode == 'readonly') {
                                cell = '<span style="color:#000;" class="oe_timesheet_weekly_box oe_timesheet_weekly_input" data-date="' + room_data.date + '" data-day-count="' + day_count + '" data-room="' + room_id + '">' + room_data.price + '</span>'
                            } else {
                                cell = '<input style="color:#000;" data-date="' + room_data.date + '" name="room_price" class="oe_timesheet_weekly_input" pattern="[0-9]" type="text" data-day-count="' + day_count + '" data-room="' + room_id + '" value="' + room_data.price + '">';
                            }
                            price_cell.innerHTML = cell;
                            $(price_cell).addClass('input_td')

                            if (room_data.price > 0) {
                                $(price_cell).addClass('bg-success')
                            } else {
                                $(price_cell).addClass('bg-danger')
                            }
                            day_count++;
                        }
                    });

                    var total_rowprice_cell = data_row.insertCell();
                    $(total_rowprice_cell).addClass('total_rowprice_cell bg-default');
                    $(total_rowprice_cell).attr('data-room', room_id);
                    self.display_rowprice(room_id)
                    self.style_caption(room_id);
                    $(data_row).addClass('rendered');
                });
            }
        },

        render_view: function() {
            var self = this;
            self.$widget = $(QWeb.render('hotel_room_availability.RoomPricelist', {
                widget: self
            }));
            // if (!self.rendered) {
            // self.rendered = true;
            self.$el.html('');
            self.$widget.appendTo(self.$el);
            _.each(self.rooms_types, function(room) {
                self.get_room_data(room.id);
            });
            // }
        },

        initialize_content: function() {
            if (this.setting) {
                return;
            }
            var self = this;
            new Model("hotel.room").call("search_read", [
                [
                    ['active', '=', 'True']
                ]
            ]).then(function(result) {
                self.rooms_types = result;
                self.rec = self.field_manager.get_fields_values()
                if (!self.get("date_to") || !self.get("date_from")) {
                    return;
                }
                if (self.rec && self.rec.id != false) {
                    self.set({
                        "id": self.rec.id
                    });
                }
                self.date_from = self.get("date_from");
                self.date_to = self.get("date_to");
                var dates = [];
                var start = self.date_from;
                var end = self.date_to;
                while (start <= end) {
                    dates.push(start);
                    var m_start = moment(start).add(1, 'days');
                    start = m_start.toDate();
                }
                self.dates = dates;
                if (self.get('effective_readonly')) {
                    self.mode = 'readonly';
                } else {
                    self.mode = 'edit';
                }
                self.rendered = false;
                self.render_view();
            });
        },

    });
    core.form_custom_registry.add('room_pricelist', RoomPricelist);
});
