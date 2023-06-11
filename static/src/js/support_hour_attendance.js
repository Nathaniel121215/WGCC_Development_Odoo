odoo.define('true_move.support_hour_attendance', function (require) {
    "use strict";
    
    var core = require('web.core');
    var Model = require('web.Model');
    var Widget = require('web.Widget');
    var Attendance_view = require('hr_attendance.my_attendances')
    var Attendance_kiosk = require('hr_attendance.kiosk_mode')
    var Attendance_mixin = require('hr_attendance.greeting_message')
    
    var _t = core._t;
    
    var AttendanceView =Attendance_mixin.include({
    
        events: {
            "click .o_hr_attendance_button_dismiss": 'action_view_attendance_checkin',
            "click .o_hr_attendance_button_dismiss_out": 'action_view_attendance',
        },
    
        action_view_attendance_checkin: function(event){
                var self = this;
                this.return_to_main_menu = setTimeout( function() { self.do_action(self.next_action, {clear_breadcrumbs: true}); }, 10);
             },
    
         action_view_attendance: function(event){
                var self = this;
                event.stopPropagation();
                event.preventDefault();
                var  check_in = this.attendance.is_check_in
                var  check_out = this.attendance.is_check_out
                var context_context;
                context_context = {'default_attendance_id': this.attendance.id,}
                // this.do_action({
                //     name: ("Support Hour Form"),
                //     type: 'ir.actions.act_window',
                //     res_model: 'hr.support.hour.wz.info',
                //     view_mode: 'form',
                //     view_type: 'form',
                //     views: [[false, 'form'],],
                //     context:context_context,
                //     domain: [],
                //     target: 'new'
                //     })
             },
    
          farewell_message: function() {
            var self = this;
            var now = this.attendance.check_out.clone();
            var context_context;
    //        context_context = {'default_attendance_id': this.attendance.id,}
    //        self.do_action({
    //               name: ("Support Hour Form"),
    //               type: 'ir.actions.act_window',
    //               res_model: 'hr.support.hour.wz.info',
    //               view_mode: 'form',
    //               view_type: 'form',
    //               views: [[false, 'form'],],
    //               context: context_context,
    //               domain: [],
    //               target: 'new'
    //               });
            if (now.hours() < 12) {
                this.$('.o_hr_attendance_random_message').html(_t("Have a good day!"));
            } else if (now.hours() < 14) {
                this.$('.o_hr_attendance_random_message').html(_t("Have a nice lunch!"));
            } else if (now.hours() < 17) {
                this.$('.o_hr_attendance_random_message').html(_t("Have a good afternoon"));
            } else {
                this.$('.o_hr_attendance_random_message').html(_t("Have a good evening"));
            }
            this.return_to_main_menu = setTimeout( function() { self.do_action(self.next_action, {clear_breadcrumbs: true}); }, 5000); 
            }
        });
    
    });
    
    
    
    
    
    