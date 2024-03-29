odoo.define('detailed_general_ledger_report.account_report_generic_extend', function (require) {
    'use strict';

    var core = require('web.core');
    var Widget = require('web.Widget');
    var formats = require('web.formats');
    var Model = require('web.Model');
    var time = require('web.time');
    var ControlPanelMixin = require('web.ControlPanelMixin');
    var ReportWidget = require('detailed_general_ledger_report.ReportWidget');
    var Dialog = require('web.Dialog');
    var session = require('web.session');
    var framework = require('web.framework');
    var crash_manager = require('web.crash_manager');
// var account_report_generic = require('account_reports.account_report_generic');
    var _t = core._t;

    var QWeb = core.qweb;

// the aim of this client action is to fetch the html of the report and to
// play with it with an instance of `ReportWidget`
    var account_report_generic_extend = Widget.extend(ControlPanelMixin, {
        // Stores all the parameters of the action.
        init: function (parent, action) {
            this.actionManager = parent;
            this.controller_url = action.context.url;
            this.report_model = action.context.model;
            // in case of a financial report, an id is defined in the action declaration
            this.report_id = action.context.id ? parseInt(action.context.id, 10) : undefined;
            this.given_context = {};
            if (action.context.context) {
                this.given_context = action.context.context;
            }
            this.given_context.from_report_id = action.context.from_report_id;
            this.given_context.from_report_model = action.context.from_report_model;
            this.given_context.force_account = action.context.force_account;
            this.given_context.active_id = action.context.active_id;
            this.odoo_context = action.context;
            return this._super.apply(this, arguments);
        },
        willStart: function () {
            return this.get_html();
        },
        // Sets the html of the page, then creates a report widget and sets it on the page.
        set_html: function () {
            var self = this;
            var def = $.when();
            if (!this.report_widget) {
                this.report_widget = new ReportWidget(this, this.report_context, this.context_model, this.odoo_context, this.report_type);
                def = this.report_widget.appendTo(this.$el);
            }
            else {
                this.report_widget.update_context(this.given_context)
            }
            def.then(function () {
                self.report_widget.$el.html(self.html);
            });
        },
        start: function () {
            this.set_html();
            return this._super.apply(this, arguments);
        },
        /* When the report has to be reloaded with a new context (the user has chosen new options).
         Fetches the html again with the new options then sets the report widget. */
        restart: function (given_context) {
            var self = this;
            this.given_context = given_context;
            return this.get_html().then(function () {
                self.set_html();
            });
        },
        // Fetches the html and is previous report.context if any, else create it
        get_html: function () {
            var self = this;
            var defs = [];
            return new Model('account.report.context.common').call('return_context', [self.report_model, self.given_context, self.report_id]).then(function (result) {
                self.context_model = new Model(result[0]);
                self.context_id = result[1];
                // Finally, actually get the html and various data
                return self.context_model.call('get_html_and_data', [self.context_id, self.given_context], {context: session.user_context}).then(function (result) {
                    self.report_type = result.report_type;
                    self.html = result.html;
                    self.xml_export = result.xml_export;
                    self.fy = result.fy;
                    self.report_context = result.report_context;
                    self.report_context.available_companies = result.available_companies;
                    if (result.available_journals) {
                        self.report_context.available_journals = result.available_journals;
                    }
                    self.render_buttons();
                    self.render_searchview_buttons();
                    self.render_searchview();
                    self.render_pager();
                    defs.push(self.update_cp());
                    if (self.report_type.dimension) {
                        var analytic_account_options = $("select[name='analytic_account']:enabled option");
                        var analytic_tag_options = $("select[name='analytic_tag']:enabled option");

                        self.change_analytic_account_inf(analytic_account_options);
                        self.change_analytic_tag_inf(analytic_tag_options);

                        self.$searchview_buttons.find('.o_event_onchange_analytic_account').on('change', function (e) {
                            self.event_onchange_analytic_accounts(e, analytic_account_options);
                        });
                        self.$searchview_buttons.find('.o_event_onchange_analytic_tag').on('change', function (e) {
                            self.event_onchange_analytic_tags(e, analytic_tag_options);
                        });
                    }
                    return $.when.apply($, defs);
                });
            });

        },
        // Updates the control panel and render the elements that have yet to be rendered
        update_cp: function () {
            if (!this.$buttons) {
                this.render_buttons();
            }
            if (!this.$searchview_buttons) {
                this.render_searchview_buttons();
            }
            if (!this.$searchview) {
                this.render_searchview();
            }
            var status = {
                breadcrumbs: this.actionManager.get_breadcrumbs(),
                cp_content: {
                    $buttons: this.$buttons,
                    $searchview_buttons: this.$searchview_buttons,
                    $pager: this.$pager,
                    $searchview: this.$searchview
                },
            };
            return this.update_control_panel(status);
        },
        do_show: function () {
            this._super();
            this.update_cp();
        },
        render_buttons: function () {
            var self = this;
            this.$buttons = $(QWeb.render("accountReports.buttons", {xml_export: this.xml_export}));

            // pdf output
            this.$buttons.siblings('.o_account-widget-pdf').bind('click', function () {
                framework.blockUI();
                session.get_file({
                    url: self.controller_url.replace('output_format', 'pdf'),
                    complete: framework.unblockUI,
                    error: crash_manager.rpc_error.bind(crash_manager),
                });
            });

            // xls output
            this.$buttons.siblings('.o_account-widget-xlsx').bind('click', function () {
                framework.blockUI();
                session.get_file({
                    url: self.controller_url.replace('output_format', 'xlsx'),
                    complete: framework.unblockUI,
                    error: crash_manager.rpc_error.bind(crash_manager),
                });
            });

            // xml output
            this.$buttons.siblings('.o_account-widget-xml').bind('click', function () {
                // For xml exports, first check if the export can be done
                return new Model('account.financial.html.report.xml.export').call('check', [self.report_model, self.report_id]).then(function (check) {
                    if (check === true) {
                        framework.blockUI();
                        session.get_file({
                            url: self.controller_url.replace('output_format', 'xml'),
                            complete: framework.unblockUI,
                            error: crash_manager.rpc_error.bind(crash_manager),
                        });
                    } else { // If it can't be done, show why.
                        Dialog.alert(this, check, {});
                    }
                });
            });
            return this.$buttons;
        },
        toggle_filter: function (target, toggle, is_open) {
            target
                .toggleClass('o_closed_menu', !(_.isUndefined(is_open)) ? !is_open : undefined)
                .toggleClass('o_open_menu', is_open);
            toggle.toggle(is_open);
        },
        // this function is reimplemented by subclasses
        render_pager: function () {
        },
        render_searchview: function () {
            this.$searchview = '';
            return this.$searchview;
        },
        render_searchview_buttons: function () {
            var self = this;
            // Render the searchview buttons and bind them to the correct actions
            this.$searchview_buttons = $(QWeb.render("accountReports.searchView", {
                report_type: this.report_type,
                context: this.report_context
            }));
            var $dateFilter = this.$searchview_buttons.siblings('.o_account_reports_date-filter');
            var $dateFilterCmp = this.$searchview_buttons.siblings('.o_account_reports_date-filter-cmp');
            var $useCustomDates = $dateFilter.find('.o_account_reports_use-custom');
            var $CustomDates = $dateFilter.find('.o_account_reports_custom-dates');
            $useCustomDates.bind('click', function () {
                self.toggle_filter($useCustomDates, $CustomDates);
            });
            var $usePreviousPeriod = $dateFilterCmp.find('.o_account_reports_use-previous-period');
            var $previousPeriod = $dateFilterCmp.find('.o_account_reports_previous-period');
            $usePreviousPeriod.bind('click', function () {
                self.toggle_filter($usePreviousPeriod, $previousPeriod);
            });
            var $useSameLastYear = $dateFilterCmp.find('.o_account_reports_use-same-last-year');
            var $SameLastYear = $dateFilterCmp.find('.o_account_reports_same-last-year');
            $useSameLastYear.bind('click', function () {
                self.toggle_filter($useSameLastYear, $SameLastYear);
            });
            var $useCustomCmp = $dateFilterCmp.find('.o_account_reports_use-custom-cmp');
            var $CustomCmp = $dateFilterCmp.find('.o_account_reports_custom-cmp');
            $useCustomCmp.bind('click', function () {
                self.toggle_filter($useCustomCmp, $CustomCmp);
            });
            this.$searchview_buttons.find('.o_account_reports_one-filter').bind('click', function (event) {
                self.onChangeDateFilter(event); // First trigger the onchange
                var error = false;
                $('.o_account_reports_datetimepicker input').each(function () { // Parse all the values of the date pickers
                    if (error) {
                        return;
                    }
                    if ($(this).val() === "") {
                        crash_manager.show_warning({data: {message: _t('Date cannot be empty')}});
                        error = true
                        return;
                    }
                    $(this).val(formats.parse_value($(this).val(), {type: 'date'}));
                });
                if (error) {
                    return;
                }
                var report_context = { // Create the context that will be given to the restart method
                    date_filter: $(event.target).parents('li').data('value'),
                    date_from: self.$searchview_buttons.find("input[name='date_from']").val(),
                    date_to: self.$searchview_buttons.find("input[name='date_to']").val(),
                };
                if (self.date_filter_cmp !== 'no_comparison') { // Add elements to the context if needed
                    report_context.date_from_cmp = self.$searchview_buttons.find("input[name='date_from_cmp']").val();
                    report_context.date_to_cmp = self.$searchview_buttons.find("input[name='date_to_cmp']").val();
                }
                self.restart(report_context); // Then restart the report
            });
            this.$searchview_buttons.find('.o_account_reports_one-filter-cmp').bind('click', function (event) { // Same for the comparison filter
                self.onChangeCmpDateFilter(event);
                $('.o_account_reports_datetimepicker input').each(function () {
                    $(this).val(formats.parse_value($(this).val(), {type: 'date'}));
                });
                var filter = $(event.target).parents('li').data('value');
                var report_context = {
                    date_filter_cmp: filter,
                    date_from_cmp: self.$searchview_buttons.find("input[name='date_from_cmp']").val(),
                    date_to_cmp: self.$searchview_buttons.find("input[name='date_to_cmp']").val(),
                };
                if (filter === 'previous_period' || filter === 'same_last_year') {
                    report_context.periods_number = $(event.target).siblings("input[name='periods_number']").val();
                }
                self.restart(report_context);
            });
            this.$searchview_buttons.find('.o_account_reports_one-filter-bool').bind('click', function (event) { // Same for the boolean filters
                var report_context = {};
                report_context[$(event.target).parents('li').data('value')] = !$(event.target).parents('li').hasClass('selected');
                self.restart(report_context);
            });

            //including balance
            this.$searchview_buttons.find('.o_account_reports_one-filter-balance').bind('click', function (event) { // Same for the boolean filters
                var report_context = {};
                report_context.balance = $(event.target).parents('li').data('value');
                self.restart(report_context);
            });
            //end

            //including initial balance
            this.$searchview_buttons.find('.o_account_reports_one-filter-initial-balance').bind('click', function (event) { // Same for the boolean filters
                var report_context = {};
                report_context.initial_balance = $(event.target).parents('li').data('value');
                self.restart(report_context);
            });
            //end
            if (this.report_context.multi_company) { // Same for the company filter
                this.$searchview_buttons.find('.o_account_reports_one-company').bind('click', function (event) {
                    var report_context = {};
                    var value = $(event.target).parents('li').data('value');
                    if (self.report_context.company_ids.indexOf(value) === -1) {
                        report_context.add_company_ids = value;
                    }
                    else {
                        report_context.remove_company_ids = value;
                    }
                    self.restart(report_context);
                });
            }
            if (this.report_context.journal_ids) { // Same for the journal
                this.$searchview_buttons.find('.o_account_reports_one-journal').bind('click', function (event) {
                    var report_context = {};
                    var value = $(event.target).parents('li').data('value');
                    if (self.report_context.journal_ids.indexOf(value) === -1) {
                        report_context.add_journal_ids = value;
                    }
                    else {
                        report_context.remove_journal_ids = value;
                    }
                    self.restart(report_context);
                });
            }
            if (this.report_context.account_type) { // Same for the account types
                this.$searchview_buttons.find('.o_account_reports_one-account_type').bind('click', function (event) {
                    var value = $(event.target).parents('li').data('value');
                    self.restart({'account_type': value});
                });
            }
            if (this.report_type.analytic && this.report_context.analytic) { // Same for the tags filter
                this.$searchview_buttons.find(".o_account_reports_analytic_account_auto_complete").select2();
                var selection = [];
                for (i = 0; i < this.report_context.analytic_account_ids.length; i++) {
                    var analytic_account = this.report_context.analytic_account_ids[i];
                    selection.push({id: analytic_account[0], text: analytic_account[1]});
                }
                this.$searchview_buttons.find('.o_account_reports_analytic_account_auto_complete').data().select2.updateSelection(selection);

                this.$searchview_buttons.find(".o_account_reports_analytic_tag_auto_complete").select2();
                selection = [];
                var i;
                for (i = 0; i < this.report_context.analytic_tag_ids.length; i++) {
                    var analytic_tag = this.report_context.analytic_tag_ids[i];
                    selection.push({id: analytic_tag[0], text: analytic_tag[1]});
                }
                this.$searchview_buttons.find('.o_account_reports_analytic_tag_auto_complete').data().select2.updateSelection(selection);
                //dimension filter
                if (this.report_type.dimension) {
                    this.$searchview_buttons.find(".o_account_reports_analytic_dimesion_auto_complete").select2();
                    selection = {};
                    if (this.report_context.analytic_account_dimension_id.length) {
                        var analytic_dimension = this.report_context.analytic_account_dimension_id;
                        selection = {id: analytic_dimension[0], text: analytic_dimension[1]};
                    }
                    else {
                        selection = {id: "", text: 'Choose...'};
                    }
                    this.$searchview_buttons.find('.o_account_reports_analytic_dimesion_auto_complete').data().select2.updateSelection(selection);

                    // Accounts to Include
                    if (this.report_context.account_include){
                        this.$searchview_buttons.find(".o_account_reports_analytic_account_include").select2();
                        var selection = {};
                        if (this.report_context.account_include == 'active_accounts'){
                            selection = {id: "", text: _t('Only Active Analytic Accounts')};
                        }
                        if (this.report_context.account_include == 'archived_accounts'){
                            selection = {id: "", text: _t('Only Archived Analytic Accounts')};
                        }
                        if (this.report_context.account_include == 'active_archived_accounts'){
                            selection = {id: "", text: _t('Active & Archived Analytic Accounts')};
                        }
                        this.$searchview_buttons.find('.o_account_reports_analytic_account_include').data().select2.updateSelection(selection);
                    }
                    //end

                    // Tags to Include
                    if (this.report_context.tag_include){
                        this.$searchview_buttons.find(".o_account_reports_analytic_tag_include").select2();
                        var selection = {};
                        if (this.report_context.tag_include == 'active_tags'){
                            selection = {id: "", text: _t('Only Active Analytic Tags')};
                        }
                        if (this.report_context.tag_include == 'archived_tags'){
                            selection = {id: "", text: _t('Only Archived Analytic Tags')};
                        }
                        if (this.report_context.tag_include == 'active_archived_tags'){
                            selection = {id: "", text: _t('Active & Archived Analytic Tags')};
                        }
                        this.$searchview_buttons.find('.o_account_reports_analytic_tag_include').data().select2.updateSelection(selection);
                    }
                    //end
                }

                this.$searchview_buttons.find('.o_account_reports_add_analytic_account_tag').bind('click', function (event) {
                    var report_context = {};
                    var value = self.$searchview_buttons.find(".o_account_reports_analytic_account_auto_complete").select2("val");
                    report_context.analytic_account_ids = value;
                    value = self.$searchview_buttons.find(".o_account_reports_analytic_tag_auto_complete").select2("val");
                    report_context.analytic_tag_ids = value;
                    //dimension filter
                    if (self.report_type.dimension) {
                        value = self.$searchview_buttons.find(".o_account_reports_analytic_dimesion_auto_complete").select2("val");
                        report_context.analytic_account_dimension_id = parseInt(value);

                        value = self.$searchview_buttons.find(".o_account_reports_analytic_account_include").select2("val");
                        report_context.account_include = value;

                        value = self.$searchview_buttons.find(".o_account_reports_analytic_tag_include").select2("val");
                        report_context.tag_include = value;
                    }
                    self.restart(report_context);
                });
            }
            if (this.report_type.account) { // account filter
                this.$searchview_buttons.find(".o_account_reports_account_account_auto_complete").select2();
                selection = [];
                var i;
                for (i = 0; i < this.report_context.account_ids.length; i++) {
                    var account_account = this.report_context.account_ids[i];
                    if (selection.length < 20) {
                        selection.push({id: account_account[0], text: account_account[1]});
                    }
                    else {
                        alert("Can not select more than 20 accounts.");
                    }
                }
                this.$searchview_buttons.find('.o_account_reports_account_account_auto_complete').data().select2.updateSelection(selection);

                this.$searchview_buttons.find(".o_account_reports_account_type_auto_complete").select2();
                selection = [];
                var i;
                for (i = 0; i < this.report_context.account_type_ids.length; i++) {
                    var account_type = this.report_context.account_type_ids[i];
                    if (selection.length < 20) {
                        selection.push({id: account_type[0], text: account_type[1]});
                    }
                    else {
                        alert("Can not select more than 20 account types.");
                    }
                    selection.push({id: account_type[0], text: account_type[1]});
                }
                this.$searchview_buttons.find('.o_account_reports_account_type_auto_complete').data().select2.updateSelection(selection);

                this.$searchview_buttons.find('.o_account_reports_add_account_account_tag').bind('click', function (event) {
                    var report_context = {};

                    var value = self.$searchview_buttons.find(".o_account_reports_account_account_auto_complete").select2("val");
                    report_context.account_ids = value;

                    value = self.$searchview_buttons.find(".o_account_reports_account_type_auto_complete").select2("val");
                    report_context.account_type_ids = value;

                    value = self.$searchview_buttons.find("input[name='account_range']").val();
                    report_context.account_range = value;
                    self.restart(report_context);
                });
            }
            this.$searchview_buttons.find('li').bind('click', function (event) {
                event.stopImmediatePropagation();
            });
            var l10n = core._t.database.parameters; // Get the localisation parameters
            var $datetimepickers = this.$searchview_buttons.find('.o_account_reports_datetimepicker');
            var options = { // Set the options for the datetimepickers
                language: moment.locale(),
                format: time.strftime_to_moment_format(l10n.date_format),
                icons: {
                    date: "fa fa-calendar",
                },
                pickTime: false,
            };
            $datetimepickers.each(function () { // Start each datetimepicker
                $(this).datetimepicker(options);
                if ($(this).data('default-value')) { // Set its default value if there is one
                    $(this).data("DateTimePicker").setValue(moment($(this).data('default-value')));
                }
            });
            if (this.report_context.date_filter !== 'custom') { // For each foldable element in the dropdowns
                this.toggle_filter($useCustomDates, $CustomDates, false); // First toggle it so it is closed
                $dateFilter.bind('hidden.bs.dropdown', function () {
                    self.toggle_filter($useCustomDates, $CustomDates, false);
                }); // When closing the dropdown, also close the foldable element
            }
            if (this.report_context.date_filter_cmp !== 'previous_period') {
                this.toggle_filter($usePreviousPeriod, $previousPeriod, false);
                $dateFilterCmp.bind('hidden.bs.dropdown', function () {
                    self.toggle_filter($usePreviousPeriod, $previousPeriod, false);
                });
            }
            if (this.report_context.date_filter_cmp !== 'same_last_year') {
                this.toggle_filter($useSameLastYear, $SameLastYear, false);
                $dateFilterCmp.bind('hidden.bs.dropdown', function () {
                    self.toggle_filter($useSameLastYear, $SameLastYear, false);
                });
            }
            if (this.report_context.date_filter_cmp !== 'custom') {
                this.toggle_filter($useCustomCmp, $CustomCmp, false);
                $dateFilterCmp.bind('hidden.bs.dropdown', function () {
                    self.toggle_filter($useCustomCmp, $CustomCmp, false);
                });
            }
            return this.$searchview_buttons;
        },
        event_onchange_analytic_accounts: function (e, analytic_account_options) {
            this.change_analytic_account_inf(analytic_account_options);
        },
        event_onchange_analytic_tags: function (e, analytic_tag_options) {
            this.change_analytic_tag_inf(analytic_tag_options);
        },
        change_analytic_account_inf: function (analytic_account_options) {
            var select = $("select[name='analytic_account']");
            analytic_account_options.detach();
            var displayed_analytic_account = analytic_account_options;
            if (this.$searchview_buttons.find('.o_account_reports_analytic_account_include').select2("val") == 'active_accounts') {
                displayed_analytic_account = analytic_account_options.filter('[data-active="true"]');
            }
            if (this.$searchview_buttons.find('.o_account_reports_analytic_account_include').select2("val") == 'archived_accounts') {
                displayed_analytic_account = analytic_account_options.filter('[data-active="false"]');
            }
            var nb = displayed_analytic_account.appendTo(select).show().size();
            select.parent().toggle(true);
        },
        change_analytic_tag_inf: function (analytic_tag_options) {
            var select = $("select[name='analytic_tag']");
            analytic_tag_options.detach();
            var displayed_analytic_tag = analytic_tag_options;
            if (this.$searchview_buttons.find('.o_account_reports_analytic_tag_include').select2("val") == 'active_tags') {
                displayed_analytic_tag = analytic_tag_options.filter('[data-active="true"]');
            }
            if (this.$searchview_buttons.find('.o_account_reports_analytic_tag_include').select2("val") == 'archived_tags') {
                displayed_analytic_tag = analytic_tag_options.filter('[data-active="false"]');
            }
            var nb = displayed_analytic_tag.appendTo(select).show().size();
            select.parent().toggle(true);
        },
        onChangeCmpDateFilter: function (event, fromDateFilter) {
            var filter_cmp = (_.isUndefined(fromDateFilter)) ? $(event.target).parents('li').data('value') : this.report_context.date_filter_cmp;
            var filter = !(_.isUndefined(fromDateFilter)) ? $(event.target).parents('li').data('value') : this.report_context.date_filter;
            var no_date_range = !this.report_type.date_range;
            if (filter_cmp === 'previous_period' || filter_cmp === 'same_last_year') {
                var dtTo = !(_.isUndefined(fromDateFilter)) ? this.$searchview_buttons.find("input[name='date_to']").val() : this.report_context.date_to;
                var dtFrom;
                var month;
                dtTo = moment(dtTo).toDate();
                if (!no_date_range) {
                    dtFrom = !(_.isUndefined(fromDateFilter)) ? this.$searchview_buttons.find("input[name='date_from']").val() : this.report_context.date_from;
                    dtFrom = moment(dtFrom).toDate();
                }
                if (filter_cmp === 'previous_period') {
                    if (filter.search("quarter") > -1) {
                        month = dtTo.getMonth();
                        dtTo.setMonth(dtTo.getMonth() - 2);
                        dtTo.setDate(0);
                        if (dtTo.getMonth() === month - 2) {
                            dtTo.setDate(0);
                        }
                        if (!no_date_range) {
                            dtFrom.setMonth(dtFrom.getMonth() - 3);
                        }
                    }
                    else if (filter.search("year") > -1) {
                        dtTo.setFullYear(dtTo.getFullYear() - 1);
                        if (!no_date_range) {
                            dtFrom.setFullYear(dtFrom.getFullYear() - 1);
                        }
                    }
                    else if (filter.search("month") > -1) {
                        dtTo.setDate(0);
                        if (!no_date_range) {
                            dtFrom.setMonth(dtFrom.getMonth() - 1);
                        }
                    }
                    else if (no_date_range) {
                        var days_to_subtract = new Date(dtTo.getFullYear(), dtTo.getMonth() + 1, 0).getDate();
                        dtTo.setDate(dtTo.getDate() - days_to_subtract);
                    }
                    else {
                        var diff = dtTo.getTime() - dtFrom.getTime();
                        dtTo = dtFrom;
                        dtTo.setDate(dtFrom.getDate() - 1);
                        dtFrom = new Date(dtTo.getTime() - diff);
                    }
                }
                else {
                    dtTo.setFullYear(dtTo.getFullYear() - 1);
                    if (!no_date_range) {
                        dtFrom.setFullYear(dtFrom.getFullYear() - 1);
                    }
                }
                if (!no_date_range) {
                    this.$searchview_buttons.find("input[name='date_from_cmp']").parents('.o_account_reports_datetimepicker').data("DateTimePicker").setValue(moment(dtFrom));
                }
                this.$searchview_buttons.find("input[name='date_to_cmp']").parents('.o_account_reports_datetimepicker').data("DateTimePicker").setValue(moment(dtTo));
            }
        },
        onChangeDateFilter: function (event) {
            var self = this;
            var no_date_range = !this.report_type.date_range;
            var today = new Date();
            var dt;
            switch ($(event.target).parents('li').data('value')) {
                case 'today':
                    dt = new Date();
                    self.$searchview_buttons.find("input[name='date_to']").parents('.o_account_reports_datetimepicker').data("DateTimePicker").setValue(moment(dt));
                    break;
                case 'last_month':
                    dt = new Date();
                    dt.setDate(0); // Go to last day of last month (date to)
                    self.$searchview_buttons.find("input[name='date_to']").parents('.o_account_reports_datetimepicker').data("DateTimePicker").setValue(moment(dt));
                    if (!no_date_range) {
                        dt.setDate(1); // and then first day of last month (date from)
                        self.$searchview_buttons.find("input[name='date_from']").parents('.o_account_reports_datetimepicker').data("DateTimePicker").setValue(moment(dt));
                    }
                    break;
                case 'last_quarter':
                    dt = new Date();
                    dt.setMonth((moment(dt).quarter() - 1) * 3); // Go to the first month of this quarter
                    dt.setDate(0); // Then last day of last month (= last day of last quarter)
                    self.$searchview_buttons.find("input[name='date_to']").parents('.o_account_reports_datetimepicker').data("DateTimePicker").setValue(moment(dt));
                    if (!no_date_range) {
                        dt.setDate(1);
                        dt.setMonth(dt.getMonth() - 2);
                        self.$searchview_buttons.find("input[name='date_from']").parents('.o_account_reports_datetimepicker').data("DateTimePicker").setValue(moment(dt));
                    }
                    break;
                case 'last_year':
                    if (today.getMonth() + 1 < self.fy.fiscalyear_last_month || (today.getMonth() + 1 === self.fy.fiscalyear_last_month && today.getDate() <= self.fy.fiscalyear_last_day)) {
                        dt = new Date(today.getFullYear() - 1, self.fy.fiscalyear_last_month - 1, self.fy.fiscalyear_last_day, 12, 0, 0, 0);
                    }
                    else {
                        dt = new Date(today.getFullYear(), self.fy.fiscalyear_last_month - 1, self.fy.fiscalyear_last_day, 12, 0, 0, 0);
                    }
                    $("input[name='date_to']").parents('.o_account_reports_datetimepicker').data("DateTimePicker").setValue(moment(dt));
                    if (!no_date_range) {
                        dt.setDate(dt.getDate() + 1);
                        dt.setFullYear(dt.getFullYear() - 1);
                        self.$searchview_buttons.find("input[name='date_from']").parents('.o_account_reports_datetimepicker').data("DateTimePicker").setValue(moment(dt));
                    }
                    break;
                case 'this_month':
                    dt = new Date();
                    dt.setDate(1);
                    self.$searchview_buttons.find("input[name='date_from']").parents('.o_account_reports_datetimepicker').data("DateTimePicker").setValue(moment(dt));
                    dt.setMonth(dt.getMonth() + 1);
                    dt.setDate(0);
                    self.$searchview_buttons.find("input[name='date_to']").parents('.o_account_reports_datetimepicker').data("DateTimePicker").setValue(moment(dt));
                    break;
                case 'this_quarter':
                    dt = new moment();
                    self.$searchview_buttons.find("input[name='date_to']").parents('.o_account_reports_datetimepicker').data("DateTimePicker").setValue(dt.endOf('quarter'));
                    if (!no_date_range) {
                        self.$searchview_buttons.find("input[name='date_from']").parents('.o_account_reports_datetimepicker').data("DateTimePicker").setValue(dt.startOf('quarter'));
                    }
                    break;
                case 'this_year':
                    if (today.getMonth() + 1 < self.fy.fiscalyear_last_month || (today.getMonth() + 1 === self.fy.fiscalyear_last_month && today.getDate() <= self.fy.fiscalyear_last_day)) {
                        dt = new Date(today.getFullYear(), self.fy.fiscalyear_last_month - 1, self.fy.fiscalyear_last_day, 12, 0, 0, 0);
                    }
                    else {
                        dt = new Date(today.getFullYear() + 1, self.fy.fiscalyear_last_month - 1, self.fy.fiscalyear_last_day, 12, 0, 0, 0);
                    }
                    self.$searchview_buttons.find("input[name='date_to']").parents('.o_account_reports_datetimepicker').data("DateTimePicker").setValue(moment(dt));
                    if (!no_date_range) {
                        dt.setDate(dt.getDate() + 1);
                        dt.setFullYear(dt.getFullYear() - 1);
                        self.$searchview_buttons.find("input[name='date_from']").parents('.o_account_reports_datetimepicker').data("DateTimePicker").setValue(moment(dt));
                    }
                    break;
            }
            if (this.$searchview_buttons.find("input[name='date_to_cmp']").length !== 0) {
                self.onChangeCmpDateFilter(event, true);
            }
        },
    });

    core.action_registry.add("account_report_generic_extend", account_report_generic_extend);
    return account_report_generic_extend;
});
