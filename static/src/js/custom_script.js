odoo.define('true_move.custom_script', function (require) {
    "use strict";
    
    var core = require('web.core');
    var Model = require('web.Model');
    var Widget = require('web.Widget');
    var Attendance_view = require('hr_attendance.my_attendances')
   
    var QWeb = core.qweb;
    var _t = core._t;
    
    var MyAttendances = Attendance_view.include({
        events: {
                "click .o_hr_attendance_sign_in_icon": 'update_attendance',
                "click .o_hr_attendance_sign_out_icon": 'check_out_form',
            },
    //    For original attendance
        update_attendance: function () {
            var self = this;
            var hr_employee = new Model('hr.employee');
            // hr_employee.query(['attendance_state', 'name', 'country_id'])
            //     .filter([['user_id', '=', self.session.uid]])
            //     .all()
            //     .then(function (res) {
            //         console.log(res[0]);
            //     });
            hr_employee.call('attendance_manual', [[self.employee.id], 'hr_attendance.hr_attendance_action_my_attendances'])
                .then(function(result) {
                    if (result.action) {
                        self.do_action(result.action);
                    } else if (result.warning) {
                        self.do_warn(result.warning);
                    }
                });
        },
    
    // To display the form 

        check_out_form: function () {
            var self = this;
            // console.log('test')
            var hr_employee = new Model('hr.employee');
            // console.log(self)
            // self.employee_country = false
            hr_employee.query(['country_id'])
                    .filter([['user_id', '=', self.session.uid]])
                    .all()
                    .then(function (res) {
                        // console.log('test_country')
                        // console.log(res[0].country_id[1])
                        // Philippines
                        if (res[0].country_id[1] == 'Philippines') {
                            // console.log('Philippine User')
                            // this.do_action({
                            //     name: (" "),
                            //     type: 'ir.actions.act_window',
                            //     res_model: 'hr.support.hour.wz',
                            //     view_mode: 'form',
                            //     view_type: 'form',
                            //     target: 'new',
                            //     context: {'default_check_out': str(date_time_now.time()),
                            //             'default_attendance_id': attendance_obj.id,
                            //             'default_employee_name': attendance_obj.employee_id.name,
                            //             'default_random_message': random_message},
                            //     })
                            hr_employee.call('attendance_manual', [[self.employee.id], 'hr_attendance.hr_attendance_action_my_attendances'])
                                .then(function(result) {
                                    if (result.action) {
                                        self.do_action(result.action);
                                        // self.do_action({
                                        //     name: ("TD, TE, TS Form"),
                                        //     type: 'ir.actions.act_window',
                                        //     res_model: 'hr.support.hour.wz.info',
                                        //     view_mode: 'form',
                                        //     view_type: 'form',
                                        //     views: [[false, 'form'],],
                                        //     domain: [],
                                        //     target: 'new'
                                        //     })
                                    } else if (result.warning) {
                                        self.do_warn(result.warning);
                                    }
                                });
                        } else {
                            console.log('Not Philippine User')
                            self.do_action({
                                name: ("Checkout Form"),
                                type: 'ir.actions.act_window',
                                res_model: 'hr.checkout.form',
                                view_mode: 'form',
                                view_type: 'form',
                                views: [[false, 'form'],],
                                domain: [],
                                target: 'new',
                                
                                })
                          
                        }
                    });
        },
    });
    
    });
    