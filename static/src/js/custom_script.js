odoo.define('true_move.custom_script', function (require) {
    "use strict";

    var core = require('web.core');
    var Model = require('web.Model');
    var AttendanceView = require('hr_attendance.my_attendances');
    var ajax = require('web.ajax');

    var MyAttendances = AttendanceView.include({
        events: _.extend({}, AttendanceView.prototype.events, {
            "click .o_hr_attendance_sign_in_icon": 'update_attendance',
            "click .o_hr_attendance_sign_out_icon": 'check_out_form',
        }),

        update_attendance: function () {
            var self = this;
            var hr_employee = new Model('hr.employee');
            hr_employee.call('attendance_manual', [[self.employee.id], 'hr_attendance.hr_attendance_action_my_attendances'])
                .then(function (result) {
                    if (result.action) {
                        console.log("Custom Message");
                        self.do_action(result.action);
                    } else if (result.warning) {
                        self.do_warn(result.warning);
                    }
                });
        },

        check_out_form: function () {
            var self = this;
            var hr_employee = new Model('hr.employee');
            hr_employee.query(['country_id'])
                .filter([['user_id', '=', self.session.uid]])
                .all()
                .then(function (res) {
                    if (res[0].country_id[1] === 'Philippines') {
                        hr_employee.call('attendance_manual', [[self.employee.id], 'hr_attendance.hr_attendance_action_my_attendances'])
                            .then(function (result) {
                                if (result.action) {
                                    self.do_action(result.action);
                                } else if (result.warning) {
                                    self.do_warn(result.warning);
                                }
                            });
                    } else {
                        console.log('Not a Philippine User');
                        self.do_action({
                            type: 'ir.actions.act_window',
                            name: "Checkout Form",
                            res_model: 'hr.checkout.form',
                            view_mode: 'form',
                            view_type: 'form',
                            views: [[false, 'form']],
                            target: 'new',
                        }).then(function () {
                            console.log("Call the button here");
                            // Listen for click event on the button
                            $(".hr-checkout-submit-button").on("click", function () {
                                console.log("button is clicked");

                                ajax.jsonRpc('/web/dataset/call_kw', 'call', {
                                    model: 'hr.checkout.form',
                                    method: 'process_form_submission',
                                    args: [[]],
                                    kwargs: {},
                                    context: {}
                                }).then(function (result) {
                                    // Handle the response
                                    console.log("The content of Result is", result);
                                    if (result.value === true) {
                                        console.log("Tama");
                                        self.update_attendance();
                                    } else {
                                        console.log("Wrong");
                                    }
                                });

                            });

                        });
                    }
                });
        },
    });

});
