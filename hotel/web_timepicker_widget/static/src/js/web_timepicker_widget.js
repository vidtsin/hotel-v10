odoo.define('web_timepicker_widget.timepicker', function (require) {
"use strict";
var core = require('web.core');
var datepicker = require('web.datepicker');

var formats = require('web.formats');
var FieldDatetime = core.form_widget_registry.get('datetime');
var time = require('web.time');
var utils = require('web.utils');
var _t = core._t;

datepicker.DateWidget.include({
    init: function(parent, options) {
        this._super.apply(this, arguments);
        var l10n = _t.database.parameters;
        this.options = _.defaults(options || {}, {
            pickDate : this.type_of_widget !== 'timepicker',
            pickTime: this.type_of_date === 'datetime',
            useSeconds: this.type_of_date === 'datetime',
            startDate: moment({ y: 1900 }),
            endDate: moment().add(200, "y"),
            calendarWeeks: false,
            icons: {
                time: 'fa fa-clock-o',
                date: 'fa fa-calendar',
                up: 'fa fa-chevron-up',
                down: 'fa fa-chevron-down'
            },
            language : moment.locale(),
            format : time.strftime_to_moment_format((this.type_of_date === 'datetime')? (this.type_of_widget === 'timepicker')? (l10n.time_format) : (l10n.date_format + ' ' + l10n.time_format) : l10n.date_format),
        });
    },
});

var TimePickerWidget = datepicker.DateTimeWidget.extend({
    type_of_widget: "timepicker",
    parse_client: function(v) {
        return formats.parse_value(v, {"widget": this.type_of_widget});
    },
    format_client: function(v) {
        return formats.format_value(v, {"widget": this.type_of_widget});
    },
});

var TimeFieldDate = FieldDatetime.extend({
    build_widget: function() {
        return new TimePickerWidget(this);
    },
});
core.form_widget_registry.add('timepicker',TimeFieldDate);
core.list_widget_registry.add('timepicker',TimeFieldDate);

formats.format_value = function format_value(value, descriptor, value_if_empty) {
    var l10n = _t.database.parameters;
    var date_format = time.strftime_to_moment_format(l10n.date_format);
    var time_format = time.strftime_to_moment_format(l10n.time_format);
    // If NaN value, display as with a `false` (empty cell)
    if (typeof value === 'number' && isNaN(value)) {
        value = false;
    }
    //noinspection FallthroughInSwitchStatementJS
    switch (value) {
        case '':
            if (descriptor.type === 'char' || descriptor.type === 'text') {
                return '';
            }
            console.warn('Field', descriptor, 'had an empty string as value, treating as false...');
            return value_if_empty === undefined ?  '' : value_if_empty;
        case false:
        case undefined:
        case Infinity:
        case -Infinity:
            return value_if_empty === undefined ?  '' : value_if_empty;
    }
    switch (descriptor.widget || descriptor.type || (descriptor.field && descriptor.field.type)) {
        case 'id':
            return value.toString();
        case 'integer':
            return utils.insert_thousand_seps(
                _.str.sprintf('%d', value));
        case 'monetary':
        case 'float':
            var digits = descriptor.digits ? descriptor.digits : [69,2];
            digits = typeof digits === "string" ? py.eval(digits) : digits;
            var precision = digits[1];
            var formatted = _.str.sprintf('%.' + precision + 'f', value).split('.');
            formatted[0] = utils.insert_thousand_seps(formatted[0]);
            return formatted.join(l10n.decimal_point);
        case 'float_time':
            var pattern = '%02d:%02d';
            if (value < 0) {
                value = Math.abs(value);
                pattern = '-' + pattern;
            }
            var hour = Math.floor(value);
            var min = Math.round((value % 1) * 60);
            if (min == 60){
                min = 0;
                hour = hour + 1;
            }
            return _.str.sprintf(pattern, hour, min);
        case 'many2one':
            // name_get value format
            return value[1] ? value[1].split("\n")[0] : value[1];
        case 'one2many':
        case 'many2many':
            if (typeof value === 'string') {
                return value;
            }
            return _.str.sprintf(_t("(%d records)"), value.length);
        case 'datetime':
            if (typeof(value) == "string")
                value = moment(time.auto_str_to_date(value));
            else {
                value = moment(value);
            }
            return value.format(date_format + ' ' + time_format);
        case 'date':
            if (typeof(value) == "string")
                value = moment(time.auto_str_to_date(value));
            else {
                value = moment(value);
            }
            return value.format(date_format);
        case 'time':
            if (typeof(value) == "string")
                value = moment(time.auto_str_to_date(value));
            else {
                value = moment(value);
            }
            return value.format(time_format);
        case 'selection': case 'statusbar':
            // Each choice is [value, label]
            if(_.isArray(value)) {
                 return value[1];
            }
            var result = _(descriptor.selection).detect(function (choice) {
                return choice[0] === value;
            });
            if (result) { return result[1]; }
            return;
        case 'timepicker':
            if (typeof(value) == "string")
                value = moment(time.auto_str_to_date(value));
            else {
                value = moment(value);
            }
            return value.format(time_format);
        default:
            return value;
    }
}

formats.parse_value = function parse_value(value, descriptor, value_if_empty) {
    var date_pattern = time.strftime_to_moment_format(_t.database.parameters.date_format),
    time_pattern = time.strftime_to_moment_format(_t.database.parameters.time_format);
    var date_pattern_wo_zero = date_pattern.replace('MM','M').replace('DD','D'),
    time_pattern_wo_zero = time_pattern.replace('HH','H').replace('mm','m').replace('ss','s');
    switch (value) {
        case false:
        case "":
            return value_if_empty === undefined ?  false : value_if_empty;
    }
    var tmp;
    switch (descriptor.widget || descriptor.type || (descriptor.field && descriptor.field.type)) {
        case 'integer':
            do {
                tmp = value;
                value = value.replace(_t.database.parameters.thousands_sep, "");
            } while(tmp !== value);
            tmp = Number(value);
            // do not accept not numbers or float values
            if (isNaN(tmp) || tmp % 1)
                throw new Error(_.str.sprintf(_t("'%s' is not a correct integer"), value));
            return tmp;
        case 'monetary':
        case 'float':
            var tmp2 = value;
            do {
                tmp = tmp2;
                tmp2 = tmp.replace(_t.database.parameters.thousands_sep, "");
            } while(tmp !== tmp2);
            var reformatted_value = tmp.replace(_t.database.parameters.decimal_point, ".");
            var parsed = Number(reformatted_value);
            if (isNaN(parsed))
                throw new Error(_.str.sprintf(_t("'%s' is not a correct float"), value));
            return parsed;
        case 'float_time':
            var factor = 1;
            if (value[0] === '-') {
                value = value.slice(1);
                factor = -1;
            }
            var float_time_pair = value.split(":");
            if (float_time_pair.length != 2)
                return factor * parse_value(value, {type: "float"});
            var hours = parse_value(float_time_pair[0], {type: "integer"});
            var minutes = parse_value(float_time_pair[1], {type: "integer"});
            return factor * (hours + (minutes / 60));
        case 'progressbar':
            return parse_value(value, {type: "float"});
        case 'datetime':
            var datetime = moment(value, [date_pattern + ' ' + time_pattern, date_pattern_wo_zero + ' ' + time_pattern_wo_zero, moment.ISO_8601], true);
            if (datetime.isValid())
                return time.datetime_to_str(datetime.toDate());
            datetime = moment(value, [date_pattern + ' ' + time_pattern, date_pattern_wo_zero + ' ' + time_pattern_wo_zero, moment.ISO_8601]);
            if (datetime.isValid())
                return time.datetime_to_str(datetime.toDate());
            throw new Error(_.str.sprintf(_t("'%s' is not a correct datetime"), value));
        case 'date':
            var date = moment(value, [date_pattern, date_pattern_wo_zero, moment.ISO_8601], true);
            if (date.isValid())
                return time.date_to_str(date.toDate());
            date = moment(value, [date_pattern, date_pattern_wo_zero, moment.ISO_8601]);
            if (date.isValid())
                return time.date_to_str(date.toDate());
            throw new Error(_.str.sprintf(_t("'%s' is not a correct date"), value));
        case 'time':
            var _time = moment(value, [time_pattern, time_pattern_wo_zero, moment.ISO_8601], true);
            if (_time.isValid())
                return time.time_to_str(_time.toDate());
            throw new Error(_.str.sprintf(_t("'%s' is not a correct time"), value));
        case 'timepicker':
            var currentTime = new Date();
            var month = currentTime.getMonth() + 1;
            var day = currentTime.getDate();
            var year = currentTime.getFullYear();
            var final_datetime = year + '-' + month + '-' + day + ' '+ value
            value = new Date(final_datetime)
            if (typeof(value) == "string")
                value = moment(time.auto_str_to_date(value));
            else {
                value = moment(value);
            }
            var datetime = moment(value, [date_pattern + ' ' + time_pattern, date_pattern_wo_zero + ' ' + time_pattern_wo_zero, moment.ISO_8601], true);
            if (datetime.isValid())
                return time.datetime_to_str(datetime.toDate());
            datetime = moment(value, [date_pattern + ' ' + time_pattern, date_pattern_wo_zero + ' ' + time_pattern_wo_zero, moment.ISO_8601]);
            if (datetime.isValid()) {
                if (datetime.year() === 0) {
                    datetime.year(moment.utc().year());
                }
                return time.datetime_to_str(datetime.toDate());
            }
            throw new Error(_.str.sprintf(_t("'%s' is not a correct time"), value));
    }
    return value;
}

});