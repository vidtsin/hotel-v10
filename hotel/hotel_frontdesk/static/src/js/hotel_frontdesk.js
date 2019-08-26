odoo.define('hotel_frontdesk.HotelFrontdeskView', function(require) {
    "use strict";

    var core = require('web.core');
    var formats = require('web.formats');
    var Model = require('web.Model');
    var session = require('web.session');
    var KanbanView = require('web_kanban.KanbanView');
    var ajax = require('web.ajax');
    var ActionManager = require('web.ActionManager');
    var form_widgets = require('web.form_widgets');
    var Dialog = require('web.Dialog');

    var QWeb = core.qweb;
    var _t = core._t;
    var _lt = core._lt;

    var HotelFrontdeskView = KanbanView.extend({
        display_name: _lt('Frontdesk'),
        icon: 'fa-user-tie',
        view_type: "hotel_frontdesk_view",
        searchview_hidden: true,

        init: function() {
            this._super.apply(this, arguments);
            this.gantt_chart = {}
        },

        events: {
            // 'click .btn_day_filter': 'filter_day_gantt',
            // 'click .btn_week_filter': 'filter_week_gantt',
            // 'click .btn_month_filter': 'filter_month_gantt',
        },

        fetch_data: function() {
            // Overwrite this function with useful data
            return $.when();
        },

        render: function() {
            var super_render = this._super;
            var self = this;
            return this.fetch_data().then(function(result) {
                var frontedesk = QWeb.render('hotel_frontdesk.HotelFrontdesk', {
                    widget: self,
                    values: result,
                });
                super_render.call(self);
                $(frontedesk).prependTo(self.$el);
                self.init_frontdesk_view(self.$el.find('.gantt-target'));
            });
        },

        render_no_content: function(fragment) {
            var content = QWeb.render('KanbanView.nocontent', {
                content: ''
            });
            $(content).appendTo(fragment);
        },

        init_frontdesk_view: function(gantt_target) {
            var self = this;
            var frontdesk_tasks = [];
            var frontdesk_tasks_call = new Model(this.model)
                .call('room_detail').then(function(details) {
                    if (details.length <= 0) {
                        var start = new Date().toISOString().substr(0, 10);
                        var end = new Date().toISOString().substr(0, 10);

                        var ganttdata = {
                            start: start,
                            end: end,
                            name: "",
                            id: 'Task 0',
                            custom_class: "no-data"
                        };
                        details.push(ganttdata);
                    } else {
                        _.each(details, function(task) {
                            task.progress = 100;
                            if (task.title_row !== null && task.title_row) {
                                task.custom_class = 'title_row'
                                task.id = 'Title-' + task.room_id
                                task.title = task.room_name
                                task.title_row = true
                                task.resid = 'Title-' + task.room_id
                            }
                            if (task.state == 'assigned') {
                                task.custom_class = 'state_assigned'
                                task.done = false
                                task.state = 'Booked'
                            } else if (task.state == 'reserved') {
                                task.custom_class = 'state_reserved'
                                task.done = false
                                task.state = 'Reserved'
                            } else if (task.state == 'done') {
                                task.custom_class = 'state_done'
                                task.state = 'Done'
                                task.done = true
                            }
                        });
                    }
                    self.gantt_chart = new Gantt(gantt_target[0], details, {
                        // on_click: function(task) {
                        //     gantt_target.html('');
                        //     self.init_frontdesk_view(gantt_target)
                        // },
                        on_date_change: function(task, start, end) {
                            new Model('hotel.frontdesk')
                                .call("get_date_change_rate", [
                                    task.room_id,
                                    formats.parse_value(formats.format_value(start, {"widget": 'date'}), {"widget": 'date'}),
                                    formats.parse_value(formats.format_value(end, {"widget": 'date'}), {"widget": 'date'}),
                                ])
                                .done(function(result) {
                                    var $content = `
                                    <div class='col-md-12'>
                                        <div class='col-md-6'>
                                            <div class='text-center date_change_wizard'>
                                                <h2 class='text-danger'> Old Detail </h2>
                                                <div class='text-left change_wiz_block ml-10'>
                                                    <h4>
                                                        <strong> ${(task.reservation_id !== null) ? 'Reservation' : 'Folio'} No: </strong> ${task.seq_no}
                                                    </h4>
                                                    <h4>
                                                        <strong>Guest: </strong> ${task.name}
                                                    </h4>
                                                    <h4>
                                                        <strong>Room: </strong> ${task.title}
                                                    </h4>
                                                    <h4 class='data_changed_source'>
                                                        <strong>Date: </strong> ${formats.format_value(task.start, {"widget": 'date'})} <strong> - To - </strong> ${formats.format_value(task.end, {"widget": 'date'})}
                                                    </h4>
                                                    <div class='col-md-offset-4 text-right mr-25'>
                                                        <h5 class='data_changed_dest_sub'> <strong> Qty: </strong> ${task.qty} </h5>
                                                        <h5 class='data_changed_dest_sub' style='border-bottom: 1px solid #eee;'> <strong> Rate: </strong> ${formats.format_value(task.price_unit, {"widget": 'monetary'})} </h5>
                                                        <h4 class='amount_change_src'>
                                                            <strong>Amount: </strong> ${formats.format_value(task.price_subtotal, {"widget": 'monetary'})}
                                                        </h4>
                                                    </div>
                                                    <div class='col-md-offset-1'></div>
                                                </div>
                                            </div>
                                        </div>
                                        <div class='col-md-6' style='border-left:1px solid #eee'>
                                            <div class='text-center date_change_wizard'>
                                                <h2 class='text-success'> New Detail </h2>
                                                <div class='text-left change_wiz_block ml-10'>
                                                    <h4>
                                                        <strong> ${(task.reservation_id !== null) ? 'Reservation' : 'Folio'} No: </strong> ${task.seq_no}
                                                    </h4>
                                                    <h4>
                                                        <strong>Guest: </strong> ${task.name}
                                                    </h4>
                                                    <h4>
                                                        <strong>Room: </strong> ${task.title}
                                                    </h4>
                                                    <h4 class='data_changed_dest'>
                                                        <strong>Date: </strong> ${formats.format_value(start, {"widget": 'date'})} <strong> - To - </strong> ${formats.format_value(end, {"widget": 'date'})}
                                                    </h4>
                                                    <div class='col-md-offset-4 text-right mr-25'>
                                                        <h5 class='data_changed_dest_sub'> <strong> Qty: </strong> ${result.qty} </h5>
                                                        <h5 class='data_changed_dest_sub' style='border-bottom: 1px solid #eee;'> <strong> Rate: </strong> ${formats.format_value(result.new_unit_price, {"widget": 'monetary'})} </h5>
                                                        <h4 class='amount_change_dest'>
                                                            <strong>Amount: </strong> ${formats.format_value(result.new_total_price, {"widget": 'monetary'})}
                                                        </h4>
                                                    </div>
                                                    <div class='col-md-offset-1'></div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                    `;
                                    var dialog = new Dialog(this, {
                                        title: _t('Change Date'),
                                        buttons: [{
                                            text: _t('Save'),
                                            classes: 'btn-primary',
                                            close: true,
                                            click: function() {
                                                if (task.folio_line_id !== null) {
                                                    new Model('hotel.folio.line')
                                                        .call("write", [
                                                            [parseInt(task.folio_line_id)], {
                                                                checkin_date: formats.format_value(start, {
                                                                    "widget": 'date'
                                                                }),
                                                                checkout_date: formats.format_value(end, {
                                                                    "widget": 'date'
                                                                }),
                                                                price_unit: result.new_unit_price,
                                                                price_subtotal: result.new_total_price,
                                                                product_uom_qty: result.qty,
                                                            }
                                                        ])
                                                        .done(function() {
                                                            new Model('hotel.room.move.line')
                                                                .call("write", [
                                                                    [parseInt(task.id)], {
                                                                        check_in: formats.format_value(start, {
                                                                            "widget": 'date'
                                                                        }),
                                                                        check_out: formats.format_value(end, {
                                                                            "widget": 'date'
                                                                        }),
                                                                    }
                                                                ])
                                                                .done(function() {
                                                                    // console.log("UPDATED DATE move");
                                                                    // window.location.reload();
                                                                    // self.gantt_chart.refresh(details);
                                                                }).fail(function() {
                                                                    gantt_target.html('');
                                                                    self.init_frontdesk_view(gantt_target)
                                                                });
                                                        }).fail(function() {
                                                            gantt_target.html('');
                                                            self.init_frontdesk_view(gantt_target)
                                                        });
                                                }
                                                if (task.reservation_line_id !== null) {
                                                    new Model('hotel_reservation.line')
                                                        .call("write", [
                                                            [parseInt(task.reservation_line_id)], {
                                                                checkin: formats.format_value(start, {
                                                                    "widget": 'date'
                                                                }),
                                                                checkout: formats.format_value(end, {
                                                                    "widget": 'date'
                                                                }),
                                                                price_unit: result.new_unit_price,
                                                                // price_subtotal: result.new_total_price,
                                                                // qty: result.qty,
                                                            }
                                                        ])
                                                        .done(function() {
                                                            new Model('hotel.room.move.line')
                                                                .call("write", [
                                                                    [parseInt(task.id)], {
                                                                        check_in: formats.format_value(start, {
                                                                            "widget": 'date'
                                                                        }),
                                                                        check_out: formats.format_value(end, {
                                                                            "widget": 'date'
                                                                        }),
                                                                    }
                                                                ])
                                                                .done(function() {
                                                                    // console.log("UPDATED DATE move");
                                                                    // window.location.reload();
                                                                }).fail(function() {
                                                                    gantt_target.html('');
                                                                    self.init_frontdesk_view(gantt_target)
                                                                });
                                                        }).fail(function() {
                                                            gantt_target.html('');
                                                            self.init_frontdesk_view(gantt_target)
                                                        });
                                                }
                                            }
                                        }, {
                                            text: _t('Discard'),
                                            close: true,
                                            click: function() {
                                                gantt_target.html('');
                                                self.init_frontdesk_view(gantt_target)
                                            }
                                        }],
                                        $content: $content,
                                    }).open();
                                });
                        },

                        on_vertical_change: function(task, old_title, new_task_resid) {

                            new Model('hotel.frontdesk')
                                .call("get_date_change_rate", [
                                    new_task_resid.resid,
                                    formats.parse_value(formats.format_value(task.start, {"widget": 'date'}), {"widget": 'date'}),
                                    formats.parse_value(formats.format_value(task.end, {"widget": 'date'}), {"widget": 'date'}),
                                ])
                                .done(function(result) {
                                    var $content = `
                                    <div class='col-md-12'>
                                        <div class='col-md-6'>
                                            <div class='text-center date_change_wizard'>
                                                <h2 class='text-danger'> Old Detail </h2>
                                                <div class='text-left change_wiz_block ml-10'>
                                                    <h4>
                                                        <strong> ${(task.reservation_id !== null) ? 'Reservation' : 'Folio'} No: </strong> ${task.seq_no}
                                                    </h4>
                                                    <h4>
                                                        <strong>Guest: </strong> ${task.name}
                                                    </h4>
                                                    <h4 class='data_changed_source'>
                                                        <strong>Room: </strong> ${old_title}
                                                    </h4>
                                                    <h4>
                                                        <strong>Date: </strong> ${formats.format_value(task.start, {"widget": 'date'})} <strong> - To - </strong> ${formats.format_value(task.end, {"widget": 'date'})}
                                                    </h4>
                                                    <div class='col-md-offset-4 text-right mr-25'>
                                                        <h5 class='data_changed_dest_sub'> <strong> Qty: </strong> ${task.qty} </h5>
                                                        <h5 class='data_changed_dest_sub' style='border-bottom: 1px solid #eee;'> <strong> Rate: </strong> ${formats.format_value(task.price_unit, {"widget": 'monetary'})} </h5>
                                                        <h4 class='amount_change_src'>
                                                            <strong>Amount: </strong> ${formats.format_value(task.price_subtotal, {"widget": 'monetary'})}
                                                        </h4>
                                                    </div>
                                                    <div class='col-md-offset-1'></div>
                                                </div>
                                            </div>
                                        </div>
                                        <div class='col-md-6' style='border-left:1px solid #eee'>
                                            <div class='text-center date_change_wizard'>
                                                <h2 class='text-success'> New Detail </h2>
                                                <div class='text-left change_wiz_block ml-10'>
                                                    <h4>
                                                        <strong> ${(task.reservation_id !== null) ? 'Reservation' : 'Folio'} No: </strong> ${task.seq_no}
                                                    </h4>
                                                    <h4>
                                                        <strong>Guest: </strong> ${task.name}
                                                    </h4>
                                                    <h4 class='data_changed_dest'>
                                                        <strong>Room: </strong> ${new_task_resid.title}
                                                    </h4>
                                                    <h4>
                                                        <strong>Date: </strong> ${formats.format_value(task.start, {"widget": 'date'})} <strong> - To - </strong> ${formats.format_value(task.end, {"widget": 'date'})}
                                                    </h4>
                                                    <div class='col-md-offset-4 text-right mr-25'>
                                                        <h5 class='data_changed_dest_sub'> <strong> Qty: </strong> ${result.qty} </h5>
                                                        <h5 class='data_changed_dest_sub' style='border-bottom: 1px solid #eee;'> <strong> Rate: </strong> ${formats.format_value(result.new_unit_price, {"widget": 'monetary'})} </h5>
                                                        <h4 class='amount_change_dest'>
                                                            <strong>Amount: </strong> ${formats.format_value(result.new_total_price, {"widget": 'monetary'})}
                                                        </h4>
                                                    </div>
                                                    <div class='col-md-offset-1'></div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                    `;
                                    var dialog = new Dialog(this, {
                                        title: _t('Change Room'),
                                        buttons: [{
                                            text: _t('Save'),
                                            classes: 'btn-primary',
                                            close: true,
                                            click: function() {
                                                if (task.folio_line_id !== null) {
                                                    new Model('hotel.folio.line')
                                                        .call("write", [
                                                            [parseInt(task.folio_line_id)], {
                                                                room_number_id: parseInt(new_task_resid.resid),
                                                                room_id: parseInt(new_task_resid.room_id),
                                                                price_unit: result.new_unit_price,
                                                                price_subtotal: result.new_total_price,
                                                                product_uom_qty: result.qty,
                                                            }
                                                        ])
                                                        .done(function() {
                                                            new Model('hotel.room.move.line')
                                                                .call("write", [
                                                                    [parseInt(task.id)], {
                                                                        room_number_id: parseInt(new_task_resid.resid),
                                                                    }
                                                                ])
                                                                .done(function() {
                                                                    // console.log("UPDATED ROOM move");
                                                                    // window.location.reload();
                                                                }).fail(function() {
                                                                    gantt_target.html('');
                                                                    self.init_frontdesk_view(gantt_target)
                                                                });
                                                        }).fail(function() {
                                                            gantt_target.html('');
                                                            self.init_frontdesk_view(gantt_target)
                                                        });
                                                }
                                                if (task.reservation_line_id !== null) {
                                                    new Model('hotel_reservation.line')
                                                        .call("write", [
                                                            [parseInt(task.reservation_line_id)], {
                                                                room_id: parseInt(new_task_resid.room_id),
                                                                room_number_id: parseInt(new_task_resid.resid),
                                                                price_unit: result.new_unit_price,
                                                                // price_subtotal: result.new_total_price,
                                                                // qty: result.qty,
                                                            }
                                                        ])
                                                        .done(function() {
                                                            new Model('hotel.room.move.line')
                                                                .call("write", [
                                                                    [parseInt(task.id)], {
                                                                        room_number_id: parseInt(new_task_resid.resid),
                                                                    }
                                                                ])
                                                                .done(function() {
                                                                    // console.log("UPDATED ROOM move");
                                                                    // window.location.reload();
                                                                }).fail(function() {
                                                                    gantt_target.html('');
                                                                    self.init_frontdesk_view(gantt_target)
                                                                });
                                                        }).fail(function() {
                                                            gantt_target.html('');
                                                            self.init_frontdesk_view(gantt_target)
                                                        });
                                                }
                                            }
                                        }, {
                                            text: _t('Discard'),
                                            close: true,
                                            click: function() {
                                                gantt_target.html('');
                                                self.init_frontdesk_view(gantt_target)
                                            }
                                        }],
                                        $content: $content,
                                    }).open();
                                });
                        },

                        on_vertically_date_change: function(task, old_title, new_task_resid, start, end) {

                            new Model('hotel.frontdesk')
                                .call("get_date_change_rate", [
                                    new_task_resid.resid,
                                    formats.parse_value(formats.format_value(start, {"widget": 'date'}), {"widget": 'date'}),
                                    formats.parse_value(formats.format_value(end, {"widget": 'date'}), {"widget": 'date'}),
                                ])
                                .done(function(result) {
                                    var $content = `
                                    <div class='col-md-12'>
                                        <div class='col-md-6'>
                                            <div class='text-center date_change_wizard'>
                                                <h2 class='text-danger'> Old Detail </h2>
                                                <div class='text-left change_wiz_block ml-10'>
                                                    <h4>
                                                        <strong> ${(task.reservation_id !== null) ? 'Reservation' : 'Folio'} No: </strong> ${task.seq_no}
                                                    </h4>
                                                    <h4>
                                                        <strong>Guest: </strong> ${task.name}
                                                    </h4>
                                                    <h4 class='data_changed_source'>
                                                        <strong>Room: </strong> ${old_title}
                                                    </h4>
                                                    <h4 class='data_changed_source'>
                                                        <strong>Date: </strong> ${formats.format_value(task.start, {"widget": 'date'})} <strong> - To - </strong> ${formats.format_value(task.end, {"widget": 'date'})}
                                                    </h4>
                                                    <div class='col-md-offset-4 text-right mr-25'>
                                                        <h5 class='data_changed_dest_sub'> <strong> Qty: </strong> ${task.qty} </h5>
                                                        <h5 class='data_changed_dest_sub' style='border-bottom: 1px solid #eee;'> <strong> Rate: </strong> ${formats.format_value(task.price_unit, {"widget": 'monetary'})} </h5>
                                                        <h4 class='amount_change_src'>
                                                            <strong>Amount: </strong> ${formats.format_value(task.price_subtotal, {"widget": 'monetary'})}
                                                        </h4>
                                                    </div>
                                                    <div class='col-md-offset-1'></div>
                                                </div>
                                            </div>
                                        </div>
                                        <div class='col-md-6' style='border-left:1px solid #eee'>
                                            <div class='text-center date_change_wizard'>
                                                <h2 class='text-success'> New Detail </h2>
                                                <div class='text-left change_wiz_block ml-10'>
                                                    <h4>
                                                        <strong> ${(task.reservation_id !== null) ? 'Reservation' : 'Folio'} No: </strong> ${task.seq_no}
                                                    </h4>
                                                    <h4>
                                                        <strong>Guest: </strong> ${task.name}
                                                    </h4>
                                                    <h4 class='data_changed_dest'>
                                                        <strong>Room: </strong> ${new_task_resid.title}
                                                    </h4>
                                                    <h4 class='data_changed_dest'>
                                                        <strong>Date: </strong> ${formats.format_value(start, {"widget": 'date'})} <strong> - To - </strong> ${formats.format_value(end, {"widget": 'date'})}
                                                    </h4>
                                                    <div class='col-md-offset-4 text-right mr-25'>
                                                        <h5 class='data_changed_dest_sub'> <strong> Qty: </strong> ${result.qty} </h5>
                                                        <h5 class='data_changed_dest_sub' style='border-bottom: 1px solid #eee;'> <strong> Rate: </strong> ${formats.format_value(result.new_unit_price, {"widget": 'monetary'})} </h5>
                                                        <h4 class='amount_change_dest'>
                                                            <strong>Amount: </strong> ${formats.format_value(result.new_total_price, {"widget": 'monetary'})}
                                                        </h4>
                                                    </div>
                                                    <div class='col-md-offset-1'></div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                    `;
                                    var dialog = new Dialog(this, {
                                        title: _t('Change Room'),
                                        buttons: [{
                                            text: _t('Save'),
                                            classes: 'btn-primary',
                                            close: true,
                                            click: function() {
                                                if (task.folio_line_id !== null) {
                                                    new Model('hotel.folio.line')
                                                        .call("write", [
                                                            [parseInt(task.folio_line_id)], {
                                                                room_number_id: parseInt(new_task_resid.resid),
                                                                checkin_date: formats.format_value(start, {
                                                                    "widget": 'date'
                                                                }),
                                                                checkout_date: formats.format_value(end, {
                                                                    "widget": 'date'
                                                                }),
                                                                room_id: parseInt(new_task_resid.room_id),
                                                                price_unit: result.new_unit_price,
                                                                price_subtotal: result.new_total_price,
                                                                product_uom_qty: result.qty,
                                                            }
                                                        ])
                                                        .done(function() {
                                                            new Model('hotel.room.move.line')
                                                                .call("write", [
                                                                    [parseInt(task.id)], {
                                                                        room_number_id: parseInt(new_task_resid.resid),
                                                                        check_in: formats.format_value(start, {
                                                                            "widget": 'date'
                                                                        }),
                                                                        check_out: formats.format_value(end, {
                                                                            "widget": 'date'
                                                                        }),
                                                                    }
                                                                ])
                                                                .done(function() {
                                                                    // console.log("UPDATED ROOM move");
                                                                    // window.location.reload();
                                                                }).fail(function() {
                                                                    gantt_target.html('');
                                                                    self.init_frontdesk_view(gantt_target)
                                                                });
                                                        }).fail(function() {
                                                            gantt_target.html('');
                                                            self.init_frontdesk_view(gantt_target)
                                                        });
                                                }
                                                if (task.reservation_line_id !== null) {
                                                    new Model('hotel_reservation.line')
                                                        .call("write", [
                                                            [parseInt(task.reservation_line_id)], {
                                                                room_number_id: parseInt(new_task_resid.resid),
                                                                checkin: formats.format_value(start, {
                                                                    "widget": 'date'
                                                                }),
                                                                checkout: formats.format_value(end, {
                                                                    "widget": 'date'
                                                                }),
                                                                room_id: parseInt(new_task_resid.room_id),
                                                                price_unit: result.new_unit_price,
                                                                // price_subtotal: result.new_total_price,
                                                                // qty: result.qty,
                                                            }
                                                        ])
                                                        .done(function() {
                                                            new Model('hotel.room.move.line')
                                                                .call("write", [
                                                                    [parseInt(task.id)], {
                                                                        room_number_id: parseInt(new_task_resid.resid),
                                                                        check_in: formats.format_value(start, {
                                                                            "widget": 'date'
                                                                        }),
                                                                        check_out: formats.format_value(end, {
                                                                            "widget": 'date'
                                                                        }),
                                                                    }
                                                                ])
                                                                .done(function() {
                                                                    // console.log("UPDATED ROOM move");
                                                                    // window.location.reload();
                                                                }).fail(function() {
                                                                    gantt_target.html('');
                                                                    self.init_frontdesk_view(gantt_target)
                                                                });
                                                        }).fail(function() {
                                                            gantt_target.html('');
                                                            self.init_frontdesk_view(gantt_target)
                                                        });
                                                }
                                            }
                                        }, {
                                            text: _t('Discard'),
                                            close: true,
                                            click: function() {
                                                gantt_target.html('');
                                                self.init_frontdesk_view(gantt_target)
                                            }
                                        }],
                                        $content: $content,
                                    }).open();
                                });
                        },

                        // on_progress_change: function(task, progress) {
                        //     console.log(task, progress);
                        // },

                        custom_popup_html: function(task) {
                            return `
                                <div class="details-container">
                                  <h5 class="text-center"><strong>Guest: &nbsp; &nbsp;</strong>${task.name}</h5>
                                  <hr class="popup-hr"/>
                                  <p><b>Room: &nbsp; &nbsp;</b>${task.title}</p>
                                  <p><b>Status: &nbsp; &nbsp;</b>${task.state}</p>
                                  <p><b>Arrival: &nbsp; &nbsp; </b>${formats.format_value(task._start, {"widget": 'date'})}</p>
                                  <p><b>Departure: &nbsp; &nbsp;</b>${formats.format_value(task._end, {"widget": 'date'})}</p>
                                </div>
                              `;
                        },
                        header_height: 50,
                        column_width: 30,
                        step: 24,
                        view_modes: ['Day', 'Week', 'Month'],
                        bar_height: 25,
                        bar_corner_radius: 3,
                        padding: 18,
                        view_mode: 'Day',
                        date_format: 'YYYY-MM-DD',
                        language: 'en',
                    });

                    $(".bar-wrapper[data-id='Task 0']").remove(); // remove bar made by sample data

                    $(document).on('click', '.btn_day_filter', function(event) {
                        event.preventDefault();
                        self.gantt_chart.change_view_mode('Day');
                        _.each(self.$el.find('.frontdesk_filter_btn'), function(btn) {
                            if ($(btn).hasClass('btn_day_filter')) {
                                $(btn).attr('disabled', true);
                            } else {
                                $(btn).attr('disabled', false);
                            }
                        });
                    });

                    $(document).on('click', '.btn_week_filter', function(event) {
                        event.preventDefault();
                        self.gantt_chart.change_view_mode('Week')
                        _.each(self.$el.find('.frontdesk_filter_btn'), function(btn) {
                            if ($(btn).hasClass('btn_week_filter')) {
                                $(btn).attr('disabled', true);
                            } else {
                                $(btn).attr('disabled', false);
                            }
                        });
                    });

                    $(document).on('click', '.btn_month_filter', function(event) {
                        event.preventDefault();
                        self.gantt_chart.change_view_mode('Month');
                        _.each(self.$el.find('.frontdesk_filter_btn'), function(btn) {
                            if ($(btn).hasClass('btn_month_filter')) {
                                $(btn).attr('disabled', true);
                            } else {
                                $(btn).attr('disabled', false);
                            }
                        });
                    });
                });
        },

    });

    core.view_registry.add('hotel_frontdesk_view', HotelFrontdeskView);
    return HotelFrontdeskView
});
