odoo.define('partner_transaction_report.download_file_widget', function (require) {
    "use strict";

    var core = require('web.core');
    var form_common = require('web.form_common');
    var framework = require('web.framework');
    var CrashManager = require('web.CrashManager');

    var WidgetDownloadFile = form_common.FormWidget.extend({
        template: 'partner_transaction_report.WidgetDownloadFile',
        events: {
            'click': function () {
                var self = this;
                var crash_manager = new CrashManager();
                self.view.save().then(function () {
                    framework.blockUI();
                    self.session.get_file({
                        url: '/download_custom_file/',
                        data: {
                            data: JSON.stringify({
                                model: self.node.attrs['model'],
                                record_id: self.view.datarecord.id
                            })
                        },
                        complete: framework.unblockUI,
                        error: crash_manager.rpc_error.bind(crash_manager)
                    });
                });
            }
        },

        init: function() {
            this._super.apply(this, arguments);
        }
    });

    core.form_custom_registry.add('download_file', WidgetDownloadFile);
});
