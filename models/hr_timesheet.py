from odoo import api, fields, models, _
from odoo.exceptions import ValidationError,UserError
from dateutil import rrule, parser, tz
from datetimerange import DateTimeRange
from datetime import datetime, timedelta, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT,DEFAULT_SERVER_DATE_FORMAT
# imported methods from hr_employee_time_clock modules
from odoo.addons.hr_employee_time_clock.models.timesheet_analysis import check_offsett
from odoo.addons.hr_employee_time_clock.models.methods import compute_holiday_hours
from odoo.addons.hr_employee_time_clock.models.timesheet_analysis import convert_datetime_local
from odoo.addons.hr_employee_time_clock.models.timesheet_analysis import seconds
from odoo.addons.hr_employee_time_clock.models.timesheet_analysis import get_calendar_ids
import pytz

class TrueMoveHRTimesheet(models.Model):
    _inherit = 'hr_timesheet_sheet.sheet'

    domain_id = fields.Many2one('hr.domain', string='Domain')
    domain_id_display = fields.Many2one('hr.domain', related="domain_id")
    department_id_display = fields.Many2one('hr.department', related="department_id")
    contract_id_display = fields.Many2one('hr.contract', related="contract_id")
    address_id_display = fields.Many2one('res.partner', related="address_id")
    month_grace_period_used = fields.Float('Month Grace Period Used', default=0.0)
    
    @api.onchange('employee_id')
    def _onchange_employee_id_set_domain(self):
        for record in self:
            if record.employee_id:
                record.domain_id = record.employee_id.domain_id.id
                record.department_id = record.employee_id.department_id.id
    # Grace period is from hr_employee_time_clock module, modified the functions to make the monthly grace period work,
    # please find "Added codes for monthly grace period" comments to easily find modified lines
    # Added codes for monthly grace period
    # get month_grace_period_used by other timesheet on same month,year
    @api.multi
    def get_month_grace_period_used(self):
        for record in self:
            timesheets = self.search([('employee_id','=',record.employee_id.id)]).filtered(lambda rec: (datetime.strptime(rec.date_from, "%Y-%m-%d").strftime('%m') == datetime.strptime(record.date_from, "%Y-%m-%d").strftime('%m')) and (datetime.strptime(rec.date_from, "%Y-%m-%d").strftime('%Y') == datetime.strptime(record.date_from, "%Y-%m-%d").strftime('%Y')))
            month_grace_period_used = 0.0
            for timesheet in timesheets:
                if timesheet.id != record.id:
                    month_grace_period_used += timesheet.month_grace_period_used
            return month_grace_period_used
    # Added codes for monthly grace period - END
        
    @api.multi
    def count_leaves(self, date_from, employee_id, period):
        holiday_obj = self.env['hr.holidays']
        start_leave_period = end_leave_period = False
        if period.get('date_from') and period.get('date_to'):
            start_leave_period = period.get('date_from')
            end_leave_period = period.get('date_to')

        holiday_ids = holiday_obj.sudo().search(
            ['|', '&',
             ('date_from', '>=', start_leave_period),
             ('date_from', '<=', end_leave_period),
             '&', ('date_to', '<=', end_leave_period),
             ('date_to', '>=', start_leave_period),
             ('employee_id', '=', employee_id),
             ('state', '=', 'validate'),
             ('type', '=', 'remove'),
             ('_is_system_gen', '=', False)])

        leaves = []
        leave_ids = []
        for leave in holiday_ids:

            date_from_leave = convert_datetime_local(self, leave.date_from + " 00:00:00")['local_str']
            date_to_leave = convert_datetime_local(self, leave.date_to + " 00:00:00")['local_str']
            leave_date_from = convert_datetime_local(self, leave.date_from + " 00:00:00")['local_dt']
            leave_date_to = convert_datetime_local(self, leave.date_to + " 00:00:00")['local_dt']

            leave_dates = list(rrule.rrule(rrule.DAILY,
                                           dtstart=parser.parse(
                                               date_from_leave),
                                           until=parser.parse(date_to_leave)))

            for date in leave_dates:
                if date.strftime('%Y-%m-%d') == date_from.strftime('%Y-%m-%d'):
                    leaves.append(
                        (leave, leave_date_from, leave_date_to, leave.number_of_days))
                    break

        return leaves
    @api.multi
    def attendance_analysis(self, timesheet_id=None, function_call=False):
        attendance_obj = self.env['hr.attendance']
        date_format, time_format = self._get_user_datetime_format()
        # print 'self',self
        # Added codes for monthly grace period
        self.month_grace_period_used = 0
        month_grace_period_used = self.get_month_grace_period_used()
        # Added codes for monthly grace period - END
        for sheet in self:
            if sheet.id == timesheet_id:
                summary_id = self.env['hr_timesheet.summary'].search([('sheet_id', '=', sheet.id)])
                if summary_id:
                    summary_id.unlink()
                else:
                    sheet.summary_ids.unlink()
                employee_id = sheet.employee_id.id
                start_date = sheet.date_from
                end_date = sheet.date_to
                contract_id = sheet.contract_id

                attendance_obj = self.env['hr.attendance']
                previous_month_diff = self.get_previous_month_diff(employee_id, start_date)
                current_month_diff = previous_month_diff
                args = {}
                wp_calendar_atndnce_ids = []

                period = {'date_from': start_date,
                          'date_to': end_date}

                res = {
                    'previous_month_diff': previous_month_diff,
                    'hours': []
                }

                period = {'date_from': start_date,
                          'date_to': end_date
                          }
                dates = list(rrule.rrule(rrule.DAILY,
                                         dtstart=parser.parse(start_date),
                                         until=parser.parse(
                                             end_date)))
                work_current_month_diff = 0.0
                total = {'worked_hours': 0.0, 'duty_hours': 0.0,
                         'diff': current_month_diff, 'work_current_month_diff': '',
                         'auth_ot': 0.0, 'actual_ot': 0.0, 'actual_worked_hours': 0.0,
                         'core_hours': 0.0, 'core_worked': 0.0, 'tt_late_hours': 0.0}

                late_freq = 0
                grace_period = 0
                get_late = 0
                get_actual_late = 0

                is_incomplete = False
                for date in dates:
                    # print 'date',date
                    if contract_id.date_start > str(date):
                        sheet_period = DateTimeRange(start_date, end_date)
                        contract_ids = self.env['hr.contract.line'].search([('contract_id', '=', contract_id.id)])
                        # print 'contract_id!!!!!', contract_id
                        for con in contract_ids:
                            intersection = DateTimeRange(con.date_start, con.date_end).is_intersection(sheet_period)
                            if intersection:
                                contract_id = con
                                # print 'contract_id!!!!!', con
                    work_type = contract_id.working_hours.work_type or False
                    # flexi_type = contract_id.working_hours.flexi_type or False
                    opentime_weekdays = contract_id.working_hours.opentime_weekdays or False
                    duty_hr = sheet.calculate_duty_hours(contract_id, date_from=date, period=period, )
                    leaves = self.count_leaves(date, self.employee_id.id, period)
                    get_holiday = self.get_holiday(date)
                    duty_hours_from_to = self.get_duty_hours_from_to(contract_id, leaves, get_holiday, employee_id,
                                                                     date)
                    get_whr = self.get_worked_hours(self.employee_id.id, contract_id, date, duty_hr, duty_hours_from_to, leaves,
                                                    period, get_holiday)
                    remark = ''
                    if duty_hr > 0 and get_whr['actual_wh'] <= 0:
                        remark = 'ABS'
                    if ('NO CO' in get_whr['check_out']) or 'ABS' in remark:
                        is_incomplete = True
                if sheet.is_incomplete != is_incomplete:
                    sheet.write({'is_incomplete': is_incomplete})

                ctr_late = 0
                for date_line in dates:
                    official_wh = 0
                    # print 'date_line',date_line
                    dh = 0
                    # remove payroll_type
                    if str(contract_id.date_start) <= str(date_line):
                        dh = sheet.calculate_duty_hours(contract_id, date_from=date_line, period=period, )
                        if dh < 0:
                            dh = 0
                    leaves = self.count_leaves(date_line, self.employee_id.id, period)
                    holiday = self.get_holiday(date_line)

                    summary_ids = self.env['hr_timesheet.summary'].search(
                        [('date', '=', date_line.strftime('%Y-%m-%d')), ('sheet_id', '=', sheet.id)])
                    get_date = date_line.strftime(date_format)
                    get_duty_hours_from_to = self.get_duty_hours_from_to(contract_id, leaves, holiday, employee_id,
                                                                         date_line)
                    get_worked_hours = self.get_worked_hours(employee_id,contract_id, date_line, dh, get_duty_hours_from_to, leaves,
                                                             period, holiday)
                    get_authorized_ot = self.get_authorized_ot(employee_id, date_line)
                    check_in = get_worked_hours['check_in']
                    check_out = get_worked_hours['check_out']
                    worked_hours = get_worked_hours['get_total_wh']
                    if work_type == 'core' or work_type == 'core_plus':
                        get_late_hours = 0
                    else:
                        get_late_hours = self.get_late(contract_id, date_line, holiday,
                                                       self.employee_id.id, leaves, get_worked_hours)
                    diff = worked_hours - dh
                    current_month_diff += diff
                    work_current_month_diff += diff

                    # Added codes for monthly grace period
                    abs_policy_late = contract_id.absence_policy_id.mapped('line_ids').filtered(lambda line: line.use_late == True)
                    if abs_policy_late.is_grace_period_monthly == True:
                        late_in = get_worked_hours['late_in']
                        if late_in > 0:
                            abs_late = contract_id.absence_policy_id.mapped('line_ids').filtered(lambda line: line.use_late == True)
                            if abs_late:
                                total_grace_period = abs_late.active_after
                                grace_period_used = self.search([('id','=',self.id)], limit=1).month_grace_period_used
                                other_timesheet_grace_period_used = month_grace_period_used
                                total_grace_period_used = grace_period_used + other_timesheet_grace_period_used
                                total_remaining_grace_period = total_grace_period - total_grace_period_used
                                leave_hours_late = 0.00
                                half_am = False
                                if leaves:
                                    if leaves[0][0].req_type in ['half_am','hours']:
                                        leave_hours_late = leaves[0][0].number_of_days_temp
                                        if leaves[0][0].req_type in ['half_am']:
                                            leave_hours_late += 1
                                            half_am = True
                                if total_remaining_grace_period > 0:
                                    if (round(total_remaining_grace_period, 2) - round(late_in, 2)) > 0:
                                        self.month_grace_period_used += late_in
                                    else:
                                        late_in_original = late_in
                                        late_check = False
                                        late_check2 = False
                                        if leave_hours_late:
                                            if half_am == True:
                                                if late_in > 4:
                                                    late_in = round(late_in, 2) - leave_hours_late
                                                else:
                                                    late_in = 0
                                            else:
                                                if round(late_in, 2) - leave_hours_late >= 0:
                                                    late_in = round(late_in, 2) - leave_hours_late
                                            if round(total_remaining_grace_period, 2) - round(late_in, 2) >= 0:
                                                if late_in != 0:
                                                    self.month_grace_period_used += round(total_remaining_grace_period, 2) - (round(total_remaining_grace_period, 2) - round(late_in, 2))
                                                late_check = True
                                                late_in = leave_hours_late
                                            else:
                                                self.month_grace_period_used += total_remaining_grace_period
                                                if round(late_in, 2) - leave_hours_late > 0:
                                                    late_in = leave_hours_late + total_remaining_grace_period
                                                else:
                                                    late_in = total_remaining_grace_period
                                        else:
                                            if (round(late_in, 2) - round(total_remaining_grace_period, 2)) > 0:
                                                late_in = round(late_in, 2) - round(total_remaining_grace_period, 2)
                                                if get_worked_hours['actual_wh'] < get_worked_hours['actual_wh'] + (late_in_original - late_in):
                                                    if dh == get_worked_hours['actual_wh']:
                                                        late_in = (late_in_original + late_in)
                                                        late_check2 = True
                                            self.month_grace_period_used += total_remaining_grace_period
                                        if get_worked_hours['actual_wh'] >= 8 or get_worked_hours['total_wh'] < 8:
                                            if (get_worked_hours['actual_wh'] + (late_in_original - late_in) > get_worked_hours['actual_wh']) and (get_worked_hours['actual_wh'] >= 8):
                                                get_worked_hours['actual_wh'] = get_worked_hours['actual_wh'] - (late_in_original - late_in)
                                            else:
                                                get_worked_hours['actual_wh'] = get_worked_hours['actual_wh'] + (late_in_original - late_in)
                                                late_in = total_remaining_grace_period
                                        if late_check == True:
                                            late_in = late_in_original
                                        if late_check2 == True:
                                            late_in = (late_in - late_in_original)
                                        get_late_hours['late'] = round(late_in_original - late_in, 2)
                                        get_late_hours['actual_late'] = round(late_in_original - late_in, 2)
                                else:
                                    if get_worked_hours['actual_wh'] >= 8 or get_worked_hours['total_wh'] < 8:
                                        if leave_hours_late:
                                            get_worked_hours['actual_wh'] = get_worked_hours['actual_wh']
                                            late_in -= leave_hours_late
                                        else:
                                            if dh == 8:
                                                if get_worked_hours['actual_wh'] >= 8:
                                                    get_worked_hours['actual_wh'] = get_worked_hours['actual_wh'] - late_in
                                                else:
                                                    get_worked_hours['actual_wh'] = get_worked_hours['actual_wh']
                                            elif dh == 5:
                                                get_worked_hours['actual_wh'] = get_worked_hours['actual_wh'] - late_in
                                            else:
                                                get_worked_hours['actual_wh'] = get_worked_hours['actual_wh']
                                                if (get_worked_hours['actual_wh'] == dh) and late_in:
                                                    get_worked_hours['actual_wh'] = get_worked_hours['actual_wh'] - late_in
                                    get_late_hours['late'] = round(late_in, 2)
                                    get_late_hours['actual_late'] = round(late_in, 2)
                    # Added codes for monthly grace period - END

                    if get_late_hours:
                        get_late = get_late_hours['late']
                        get_actual_late = get_late_hours['actual_late']

                    auto_nd_hrs = 0
                    # ot_line_ids = []
                    if sheet.auto_overtime:
                        get_actual_ot = 0
                        for rec in summary_ids:
                            get_actual_ot = rec.actual_ot
                            if rec.actual_ot:
                                auto_nd_hrs = self._get_auto_nd(date_line)
                    else:
                        get_actual_ot = self.get_actual_ot(date_line, contract_id, diff, get_authorized_ot,
                                                           get_worked_hours)
                        # print 'get',get_actual_ot
                        # # ot_line_ids.append(get_actual_ot['ot_id'])

                    if sheet.auto_worked_hours and work_type != 'core':
                        get_actual_worked_hours = 0
                        for rec in summary_ids:
                            get_actual_worked_hours = rec.actual_worked_hours
                    else:
                        get_actual_worked_hours = get_worked_hours['actual_wh']
                    # print('get_actual_worked_hours', get_actual_worked_hours)
                        # if not work_type == 'shift':
                        #     get_actual_worked_hours = get_actual_worked_hours - get_late
                    # print 'get_act_wh', get_actual_worked_hours

                    if opentime_weekdays and sheet.auto_overtime_compute:
                        if sheet.auto_overtime:
                            get_actual_ot = get_actual_ot['get_ot']
                        else:
                            get_actual_ot = get_worked_hours['total_wh'] - dh

                    if opentime_weekdays and sheet.auto_worked_hours:
                        get_ut = 0
                        for rec in summary_ids:
                            if rec.actual_worked_hours > 0 and rec.actual_worked_hours < dh:
                                get_ut = dh - rec.actual_worked_hours
                    else:
                        if work_type == 'core' or work_type == 'core_plus':
                            get_ut = 0
                        else:
                            get_ut = self.get_undertime(contract_id, date_line, holiday,
                                                        leaves, self.employee_id.id,
                                                        get_duty_hours_from_to['duty_hours_from'],
                                                        get_duty_hours_from_to['duty_hours_to'], get_worked_hours, dh)
                    if get_ut:
                        if leaves:
                            if leaves[0][0].req_type in ['half_pm']:
                                get_ut -= leaves[0][0].number_of_days_temp
                                if get_ut < 0:
                                    get_ut = 0
                                
                    weekdays_list = [ 'Mon', 'Tue', 'Wed', 'Thu', 'Fri']
                    day_date = date_line.strftime('%a')
                    get_remarks = ''
                    if day_date in weekdays_list:
                        get_remarks = self.get_remarks(date_line, work_type, leaves, diff,
                                                    get_actual_worked_hours, get_worked_hours, get_actual_ot['get_ot'],
                                                    dh,worked_hours, get_late, get_ut, holiday)
                    get_core_hours = self.get_core_hours(contract_id, employee_id, date_line)
                    if work_type == 'core' or work_type == 'core_plus':
                        get_abs = 0
                    else:
                        get_abs = 0
                        # remove payroll_type
                        if str(contract_id.date_start) <= str(date_line):
                            get_abs = self.get_abs(date_line, get_worked_hours, dh, get_actual_late, get_ut)
                            if get_abs <= 1:
                                get_abs = 0
                    get_night_diff = self._get_input_ND(contract_id, date_line, holiday)

                    official_dh = 0
                    if get_duty_hours_from_to['calendar_atndnce_ids']:
                        if work_type != 'shift':
                            official_dh = contract_id.working_hours.no_hours_day
                        else:
                            # print 'DURATION', get_duty_hours_from_to['calendar_atndnce_ids']
                            official_dh = get_duty_hours_from_to['calendar_atndnce_ids'].duration
                        # print 'get_duty_hours_from_to', get_duty_hours_from_to['calendar_atndnce_ids']

                    leave_hours = 0.00
                    leave_id = ''
                    leave_ids = []
                    if leaves:
                        # leave_ids.append(leaves[0][0].id)
                        if day_date in weekdays_list:
                            leave_id = leaves[0][0].id
                            if leaves[0][0].number_of_days_temp < 1:
                                leave_hours = contract_id.working_hours.no_hours_day * leaves[0][0].number_of_days_temp
                            elif leaves[0][0].req_type in ['half_am','half_pm','hours']:
                                leave_hours = leaves[0][0].number_of_days_temp
                            else:
                                leave_hours = contract_id.working_hours.no_hours_day

                    # When The employee is absent before Holiday .
                    timesheet_remarks = ''
                    timesheet_summary = ''
                    holiday_hours = 0.00
                    holiday_ids = []

                    if holiday:
                        for hol in holiday:
                            holiday_record = compute_holiday_hours(sheet, date_line, hol,get_actual_ot['get_ot'],official_dh)
                            holiday_hours = holiday_record['holiday_hours']
                            get_abs = holiday_record['absent_hours']
                            get_remarks = holiday_record['remarks'] if holiday_record['remarks'] else get_remarks
                            holiday_ids.append(hol.id)
                    # print 'holiday',holiday_ids
                    # print 'leave_ids',leave_ids
                    # print 'holiday_ids',holiday_ids
                    if diff == 0:
                        disp_diff = ''
                    else:
                        disp_diff = str(round(diff, 2))

                    get_ot = round(get_actual_ot['get_ot'], 2)

                    core_actual_wh = 0.00

                    if get_core_hours['total_core'] > 0:
                        disp_total_core = attendance_obj.float_time_convert(get_core_hours['total_core'])
                    else:
                        disp_total_core = ''

                    if get_worked_hours['core_worked'] > 0:
                        # disp_core_worked = attendance_obj.float_time_convert(get_worked_hours['core_worked'])
                        disp_core_worked = str(round(get_worked_hours['core_worked'], 2))
                    else:
                        disp_core_worked = ''

                    if dh == 0 and not get_remarks and work_type != 'open':
                        is_restday = True
                    elif work_type == 'open' and work_type == 'daily' and get_actual_worked_hours <= 0 and not get_remarks:
                        is_restday = True
                    else:
                        is_restday = False

                    if date_line:
                        atndance_summary_obj = self.env['hr_timesheet.summary']

                        if (not get_remarks == 'ABS' and holiday) or leaves:
                            official_wh = self.working_hours.no_hours_day
                        else:
                            official_wh = get_actual_worked_hours

                        if work_type in ['core', 'core_plus']:
                            get_actual_worked_hours = round(get_worked_hours['core_worked'], 2)

                        # if get_ot and not dh:
                        #    get_actual_worked_hours = get_ot

                        if holiday:
                            get_actual_worked_hours = 0.00

                        args = {'sheet_id': self.id,
                                'date': date_line.strftime(date_format),
                                'check_in': check_in,
                                'check_out': check_out,
                                'employee_id': employee_id,
                                'duty_hours': 0 if work_type in ['core','core_plus'] else dh,
                                'worked_hours': worked_hours,
                                'diff': diff,
                                'auth_ot': get_authorized_ot['ot_hour'],
                                'actual_ot': get_ot,
                                'actual_worked_hours': get_actual_worked_hours,
                                'late_hours': get_late,
                                'ut_hours': get_ut,
                                'abs_hours': get_abs,
                                'night_diff': get_night_diff['actual_nd'] + get_actual_ot['nd_ot'],
                                'remarks': get_remarks,
                                'official_wh': official_wh,
                                'holiday_hours': holiday_hours,
                                'leave_hours': leave_hours,
                                'official_dh': official_dh,
                                'leave_id':leave_id,
                                }

                        summary_id = atndance_summary_obj.create(args)
                        summary_id.holiday_ids = [[6, 0, holiday_ids]]
                        # summary_id.ot_line_ids = get_actual_ot['ot_line_id']
                        check_offset = check_offsett(sheet)
                        if check_offset:
                            summary_id.write({
                                'late_hours': check_offset['late_hours'],
                                'ut_hours': check_offset['ut_hours'],
                                'actual_ot': check_offset['actual_ot'],
                                'actual_worked_hours': check_offset['actual_worked_hours'],
                            })

                    if function_call:
                        res['hours'].append({
                            _('Date'): '' if not summary_id.date else datetime.strptime(summary_id.date,
                                                                                        '%Y-%m-%d').strftime(
                                '%m/%d/%Y'),
                            _('Duty From'): get_duty_hours_from_to['duty_hours_from'],
                            _('Duty To'): get_duty_hours_from_to['duty_hours_to'],
                            # _('Duty Hours'):disp_dh,
                            _('Sched Hours'): '' if not summary_id.duty_hours else str(summary_id.duty_hours),
                            # _('Core Hours From'): get_core_hours['core_hours_from'],
                            # _('Core Hours To'): get_core_hours['core_hours_to'],
                            # _('Core Hours'): disp_total_core,
                            _('Worked From'): '' if not summary_id.check_in else str(summary_id.check_in),
                            _('Worked To'): '' if not summary_id.check_out else str(summary_id.check_out),
                            _('Worked Hours'): '' if not summary_id.worked_hours else str(summary_id.worked_hours),
                            _('Difference'): disp_diff,
                            _('Core Worked'): disp_core_worked,
                            _('OT From'): get_authorized_ot['hour_from'],
                            _('OT To'): get_authorized_ot['hour_to'],
                            _('auth_ot_hour'): '' if not summary_id.auth_ot else str(summary_id.auth_ot),
                            _('actual_ot'): '' if not summary_id.actual_ot else str(summary_id.actual_ot),
                            _('actual_wh'): '' if not summary_id.actual_worked_hours else str(
                                summary_id.actual_worked_hours),
                            _('late_hours'): '' if not summary_id.late_hours else str(summary_id.late_hours),
                            _('Remarks'): summary_id.remarks,
                            _('Rest Day'): is_restday,

                        })

                    else:
                        res['hours'].append({
                            'name': date_line.strftime(date_format),
                            'dh': attendance_obj.float_time_convert(dh),
                            'worked_hours': attendance_obj.float_time_convert(
                                worked_hours),
                            'diff': self.sign_float_time_convert(diff),
                            'running': self.sign_float_time_convert(
                                current_month_diff)})
                    if work_type not in ['core', 'core_plus']:
                        total['duty_hours'] += dh
                    else:
                        total['duty_hours'] = dh

                    total['worked_hours'] += worked_hours
                    total['diff'] += diff
                    total['work_current_month_diff'] = work_current_month_diff
                    # total['core_hours'] += get_core_hours['total_core']
                    # total['core_worked'] += get_worked_hours['core_worked']
                    total['auth_ot'] += get_authorized_ot['ot_hour']
                    # print 'get_actual_ot',get_actual_ot['get_ot']
                    total['actual_ot'] += get_ot
                    if get_actual_worked_hours > 0:
                        total['actual_worked_hours'] += get_actual_worked_hours
                    total['tt_late_hours'] += get_late
                    if work_type in ['core','core_plus']:
                        if total['actual_worked_hours'] < get_duty_hours_from_to['calendar_atndnce_ids'].sched_hours:
                            total['core_remarks'] = 'UT'
                        else:
                            total['core_remarks'] = ''
                    res['total'] = total

                return res
    @api.multi
    def get_worked_hours(self, employee_id, contract_id, date_line, dh, duty_hours, leaves, period, holiday):
        sdtf = DEFAULT_SERVER_DATETIME_FORMAT
        dtf = '%Y-%m-%d %H:%M'
        df = '%Y-%m-%d'
        get_date = date_line.strftime('%Y-%m-%d')
        # contract_id = contract_id
        attendance_obj = self.env['hr.attendance']
        work_type = contract_id.working_hours.work_type
        # flexi_type = contract_id.working_hours.flexi_type
        # get_flexi_type = contract_id.working_hours.flexi_type
        opentime_weekdays = contract_id.working_hours.opentime_weekdays
        grace_period = 0
         # Added codes for monthly grace period
        late_in = 0
        # Added codes for monthly grace period - END

        if contract_id.absence_policy_id:
            abs_late = contract_id.absence_policy_id.mapped('line_ids').filtered(lambda line: line.use_late == True)
            if abs_late:
                grace_period = abs_late.active_after

        calendar_atndnce_ids = []

        rec_ctr = 0
        check_in = ''
        check_out = ''

        ci_ctr = 0
        co_ctr = 0
        diff_out_in = 0
        actual_wh = 0
        core_worked = 0
        check_out_ttf = 0
        check_out_dte = ''
        exc_hrs = 0
        diff = 0
        total_get_wh = 0
        get_total_wh = 0
        total_wh = 0
        duty_to = ''
        duty_from = ''
        lcl_check_out = ''

        for calendar in duty_hours['calendar_atndnce_ids']:
            if work_type != 'shift':
                calendar = calendar
            else:
                # print 'calendar', calendar
                calendar = calendar.shift_id

            duty_from = attendance_obj.float_time_convert(calendar.hour_from)
            duty_to = attendance_obj.float_time_convert(calendar.hour_to)

        var_duty_to = ''
        var_duty_from = ''
        date_duty_from = get_date + ' ' + duty_from
        date_duty_to = get_date + ' ' + duty_to
        if duty_from:
            var_duty_from = datetime.strptime(date_duty_from, "%Y-%m-%d %H:%M")
            var_duty_to = datetime.strptime(date_duty_to, "%Y-%m-%d %H:%M")

            if var_duty_to < var_duty_from:
                var_duty_to = var_duty_to + timedelta(days=1)

        res_atndnce = attendance_obj.search([('employee_id', '=', employee_id)], order='check_in asc')
        if work_type == 'shift':

            # For attendance that the check_in is in previous date
            if duty_from != duty_to:
                attendance_ids = res_atndnce.filtered(
                    lambda r: r.check_in and r.check_out and convert_datetime_local(self, r.check_in)[
                        'local_dt'] <= var_duty_to
                              and convert_datetime_local(self, r.check_out)['local_dt'] >= var_duty_from)
            else:
                ot_det = self.env['hr.overtime.line'].search([('overtime_id.state', '=', 'approve'),
                                                             ('start_date', '=', get_date)], limit=1).filtered(
                    lambda o: employee_id in o.overtime_id.emp_ids.ids)

                start_date = get_date + ' ' + attendance_obj.float_time_convert(ot_det.start_time)
                end_date = get_date + ' ' + attendance_obj.float_time_convert(ot_det.end_time)

                start_date = datetime.strptime(start_date, "%Y-%m-%d %H:%M")
                end_date = datetime.strptime(end_date, "%Y-%m-%d %H:%M")
                attendance_ids = res_atndnce.filtered(lambda r: r.check_in and r.check_out
                                                                and convert_datetime_local(self, r.check_in)[
                                                                    'local_dt'] <= end_date
                                                                and convert_datetime_local(self, r.check_out)[
                                                                    'local_dt'] >= start_date)
            # print 'attnd',attendance_ids
        else:
            attendance_ids = res_atndnce.filtered(
                lambda r: r.check_in and convert_datetime_local(self, r.check_in)['date'] == get_date)
        if attendance_ids:
            for rec in attendance_ids:
                # print 'rec',rec.check_in
                sched_hours = 0
                diff_out_in = 0
                get_check_out = 'NO CO'

                dt_localize_checkin = convert_datetime_local(self, rec.check_in)
                get_check_in = dt_localize_checkin['time_hm']
                check_in_ttf = dt_localize_checkin['ttf']
                check_in_dte = dt_localize_checkin['date']
                lcl_check_in = dt_localize_checkin['local_dt']

                if rec.check_out:
                    dt_localize_checkout = convert_datetime_local(self, rec.check_out)
                    check_out_dte = dt_localize_checkout['date']
                    lcl_check_out = dt_localize_checkout['local_dt']
                    if (str(date_line.date()) == str(check_out_dte)) or (check_out_dte > check_in_dte):
                        get_check_out = dt_localize_checkout['time_hm']
                        check_out_ttf = dt_localize_checkout['ttf']

                if leaves:
                    for leave in leaves:
                        leave_dte_from = leave[1]
                        leave_dte_to = leave[2]
                        date_yesterday = datetime.strftime(leave[1] - timedelta(1), df)
                        date_tom = datetime.strftime(leave[1] + timedelta(1), df)
                        before_leave_att = res_atndnce.filtered(lambda r: r.check_in and check_in_dte == date_yesterday)
                        after_leave_att = res_atndnce.filtered(lambda r: r.check_in and check_in_dte == date_tom)

                        abs_leave = contract_id.absence_policy_id.mapped('line_ids').filtered(
                            lambda line: line.use_leave == True and line.holiday_status_id.id == leave[
                                0].holiday_status_id.id)
                        # print 'ABS LEAVE',abs_leave

                        # if abs_leave:
                        #     lv_day_before = abs_leave.day_before
                        #     lv_day_after = abs_leave.day_after

                        #     if not before_leave_att and lv_day_before:
                        #         leave[0].sudo().write({'state': 'refuse'})
                        #     elif not after_leave_att and lv_day_after:
                        #         leave[0].sudo().write({'state': 'refuse'})

                        # if rec.check_in and rec.check_out:
                        #     if lcl_check_in >= leave_dte_from and lcl_check_out <= leave_dte_to:
                        #         leave[0].sudo().write({'state': 'refuse'})
                        #     elif lcl_check_in <= leave_dte_from and lcl_check_out >= leave_dte_to:
                        #         leave[0].sudo().write({'state': 'refuse'})
                        #     elif lcl_check_in >= leave_dte_from and lcl_check_in < leave_dte_to:
                        #         leave[0].sudo().write({'state': 'refuse'})
                        #     elif lcl_check_out > leave_dte_from and lcl_check_out <= leave_dte_to:
                        #         leave[0].sudo().write({'state': 'refuse'})

                """ start: work hours from to display"""

                if check_in_dte == check_out_dte or check_in_dte:
                    wh_in = ' ' + get_check_in
                    wh_out = ' ' + get_check_out
                else:
                    wh_in = '(' + str(datetime.strptime(check_in_dte, df).day) + ')' + ' ' + get_check_in
                    wh_out = '(' + str(datetime.strptime(check_out_dte, df).day) + ')' + ' ' + get_check_out

                if date_line.date() != lcl_check_in.date() and duty_from == '00:00':
                    wh_in = ''
                    wh_out = ''

                if ci_ctr > 0:
                    check_in = check_in + '/' + wh_in
                else:
                    check_in = check_in + wh_in
                ci_ctr += 1

                if co_ctr > 0:
                    check_out = check_out + '/' + wh_out
                else:
                    check_out = check_out + wh_out
                co_ctr += 1

                if rec.check_out and rec.check_in:
                    time_total_wh = datetime.strptime(rec.check_out, sdtf) - datetime.strptime(rec.check_in, sdtf)
                    get_total_wh += seconds(time_total_wh) / 3600
                """ end: work hours from to display"""

                for calendar in duty_hours['calendar_atndnce_ids']:
                    get_wh = 0
                    if work_type != 'shift':
                        calendar = calendar
                    else:
                        calendar = calendar.shift_id
                    float_duty_hr_from = calendar.hour_from
                    duty_hr_from = attendance_obj.float_time_convert(calendar.hour_from)
                    duty_hr_to = attendance_obj.float_time_convert(calendar.hour_to)
                    exc_hr_from = attendance_obj.float_time_convert(calendar.exc_hr_from)
                    exc_hr_to = attendance_obj.float_time_convert(calendar.exc_hr_to)

                    exc_hr_from = get_date + ' ' + exc_hr_from
                    exc_hr_to = get_date + ' ' + exc_hr_to

                    var_exc_hr_from = ''
                    var_exc_hr_to = ''
                    var_exc_hr_from = datetime.strptime(exc_hr_from, dtf)
                    var_exc_hr_to = datetime.strptime(exc_hr_to, dtf)

                    sched_hours = dh
                    exc_hrs = 0

                    if check_out_dte == check_in_dte or check_out == 'NO CO' or self.working_hours.name == '48 Hours/Week':
                        if check_in_ttf <= calendar.exc_hr_from and check_out_ttf >= calendar.exc_hr_to:
                            exc_hrs = calendar.exc_hr_to - calendar.exc_hr_from
                        elif check_in_ttf > calendar.exc_hr_from and check_in_ttf < calendar.exc_hr_to:
                            exc_hrs = calendar.exc_hr_to - check_in_ttf
                        elif check_out_ttf > calendar.exc_hr_from and check_out_ttf < calendar.exc_hr_to:
                            exc_hrs = check_out_ttf - calendar.exc_hr_from

                        total_wh = get_total_wh - exc_hrs

                    elif check_out_dte != check_in_dte and get_check_out != 'NO CO':
                        if var_exc_hr_from < var_duty_from:
                            var_exc_hr_from = var_exc_hr_from + timedelta(days=1)
                        if var_duty_from > var_exc_hr_to:
                            var_exc_hr_to = var_exc_hr_to + timedelta(days=1)

                        if lcl_check_in <= var_exc_hr_from and lcl_check_out >= var_exc_hr_to:
                            if calendar.exc_hr_to < calendar.exc_hr_from:
                                exc_hrs = (calendar.exc_hr_to + 24.0) - calendar.exc_hr_from
                            else:
                                exc_hrs = calendar.exc_hr_to - calendar.exc_hr_from

                        elif lcl_check_in > var_exc_hr_from and lcl_check_in < var_exc_hr_to:
                            if var_exc_hr_to.date() == var_duty_to.date() and lcl_check_in.date() == var_duty_to.date():
                                exc_hrs = calendar.exc_hr_to - check_in_ttf
                            elif var_exc_hr_to.date() == var_duty_to.date():
                                exc_hrs = (calendar.exc_hr_to + 24.0) - check_in_ttf
                            elif lcl_check_in.date() == var_duty_to.date():
                                exc_hrs = calendar.exc_hr_to - (check_in_ttf + 24.0)
                            else:
                                exc_hrs = calendar.exc_hr_to - check_in_ttf

                        elif lcl_check_out > var_exc_hr_from and lcl_check_out < var_exc_hr_to:
                            if lcl_check_out.date() == var_duty_to.date() and var_exc_hr_from.date() == var_duty_to.date():
                                exc_hrs = check_out_ttf - calendar.exc_hr_from
                            elif lcl_check_out.date() == var_duty_to.date():
                                exc_hrs = (check_out_ttf + 24.0) - calendar.exc_hr_from
                            elif var_exc_hr_from.date() == var_duty_to.date():
                                exc_hrs = check_out_ttf - (calendar.exc_hr_from + 24.0)
                            else:
                                exc_hrs = check_out_ttf - calendar.exc_hr_from
                        if date_line.date() != lcl_check_in.date():
                            get_total_wh = 0
                        total_wh = get_total_wh - exc_hrs

                    if get_check_in and get_check_out != 'NO CO':
                        if work_type == 'weekly' or work_type == 'daily' or opentime_weekdays:
                            diff_in = 0
                            diff_out = 0
                            if get_check_in != get_check_out:
                                # added condition if self.working_hours.name == '48 Hours/Week
                                # to validate late attendance with checkout in next day.
                                if check_out_dte == check_in_dte or self.working_hours.name == '48 Hours/Week':
                                    if check_out_dte != check_in_dte and self.working_hours.name == '48 Hours/Week':
                                        get_check_out = '23:59'
                                    if get_check_in >= duty_hr_from or get_check_out >= duty_hr_from:
                                        # if check_in_dte == check_out_dte:
                                        if str(lcl_check_in) <= exc_hr_from:
                                            if str(lcl_check_out) >= exc_hr_to:
                                                diff = calendar.exc_hr_to - calendar.exc_hr_from
                                            if str(lcl_check_out) < exc_hr_to:
                                                diff = check_out_ttf - calendar.exc_hr_from
                                        elif str(lcl_check_in) > exc_hr_from:
                                            if str(lcl_check_out) >= exc_hr_to:
                                                diff = calendar.exc_hr_to - check_in_ttf
                                            elif str(lcl_check_out) < exc_hr_to:
                                                diff = check_out_ttf - check_in_ttf

                                        if get_check_in <= duty_hr_from and get_check_out >= duty_hr_to:
                                            get_wh = calendar.hour_to - calendar.hour_from

                                        elif get_check_in > duty_hr_from:
                                            if get_check_out >= duty_hr_to:
                                                get_wh = calendar.hour_to - check_in_ttf
                                            else:
                                                get_wh = check_out_ttf - check_in_ttf

                                        elif get_check_in <= duty_hr_from:

                                            if get_check_out >= duty_hr_to:
                                                get_wh = calendar.hour_to - calendar.hour_from
                                            else:
                                                get_wh = check_out_ttf - calendar.hour_from

                                        if get_wh > 0 and diff > 0:
                                            get_wh = get_wh - diff
                                        if get_wh > 0:
                                            diff_out_in += get_wh
                                         # Added codes for monthly grace period
                                        if (check_in_ttf - float_duty_hr_from) > 0:
                                            late_in = check_in_ttf - float_duty_hr_from
                                        # Added codes for monthly grace period - END

                                        if grace_period:
                                            if round(grace_period, 2) >= round((check_in_ttf - float_duty_hr_from),
                                                                               2) and check_in_ttf > float_duty_hr_from:
                                                diff_out_in += (check_in_ttf - float_duty_hr_from)

                                else:
                                    if lcl_check_in <= var_exc_hr_from:
                                        if lcl_check_out >= var_exc_hr_to:
                                            if calendar.exc_hr_to < calendar.exc_hr_from:
                                                diff = (calendar.exc_hr_to + 24.0) - calendar.exc_hr_from
                                            else:
                                                diff = calendar.exc_hr_to - calendar.exc_hr_from

                                        if lcl_check_out < var_exc_hr_to:
                                            if var_duty_to.date() == lcl_check_out.date():
                                                if var_duty_to.date() == var_exc_hr_from.date():
                                                    diff = check_out_ttf - calendar.exc_hr_from
                                                else:
                                                    diff = (check_out_ttf + 24.0) - calendar.exc_hr_from
                                            else:
                                                if var_duty_to.date() == var_exc_hr_from.date():
                                                    diff = check_out_ttf - (calendar.exc_hr_from + 24.0)
                                                else:
                                                    diff = check_out_ttf - calendar.exc_hr_from


                                    elif lcl_check_in > var_exc_hr_from:
                                        if lcl_check_out >= var_exc_hr_to:
                                            if var_exc_hr_to.date() == var_duty_to.date() and lcl_check_in.date() == var_duty_to.date():
                                                diff = calendar.exc_hr_to - check_in_ttf
                                            elif var_exc_hr_to.date() == var_duty_to.date():
                                                diff = (calendar.exc_hr_to + 24.0) - check_in_ttf
                                            elif lcl_check_in.date() == var_duty_to.date():
                                                diff = calendar.exc_hr_to - (check_in_ttf + 24.0)
                                            else:
                                                diff = calendar.exc_hr_to - check_in_ttf

                                        elif lcl_check_out < var_exc_hr_to:
                                            if lcl_check_out.date() == var_duty_to.date():
                                                diff = (check_out_ttf + 24.0) - check_in_ttf
                                            elif lcl_check_in.date() == var_duty_to.date():
                                                diff = check_out_ttf - (check_in_ttf + 24.0)
                                            else:
                                                diff = check_out_ttf - check_in_ttf

                                    if lcl_check_in <= var_duty_from and lcl_check_out >= var_duty_to:
                                        if calendar.hour_to < calendar.hour_from:
                                            get_wh = (calendar.hour_to + 24.0) - calendar.hour_from
                                        else:
                                            get_wh = calendar.hour_to - calendar.hour_from

                                    elif lcl_check_in > var_duty_from:
                                        if lcl_check_out >= var_duty_to:
                                            if lcl_check_in.date() == var_duty_to.date() and var_exc_hr_to.date() == var_duty_to.date():
                                                get_wh = calendar.hour_to - check_in_ttf
                                            elif lcl_check_in.date() == var_duty_to.date():
                                                get_wh = calendar.hour_to - (check_in_ttf + 24.0)
                                            elif var_exc_hr_to.date() == var_duty_to.date():
                                                get_wh = (calendar.hour_to + 24.0) - check_in_ttf
                                            else:
                                                get_wh = (calendar.hour_to + 24.0) - check_in_ttf
                                        else:
                                            if lcl_check_out.date() == var_duty_to.date() and lcl_check_in.date() == var_duty_to.date():
                                                get_wh = check_out_ttf - check_in_ttf
                                            elif lcl_check_out.date() == var_duty_to.date():
                                                get_wh = (check_out_ttf + 24.0) - check_in_ttf
                                            elif lcl_check_in.date() == var_duty_to.date():
                                                get_wh = check_out_ttf - (check_in_ttf + 24.0)
                                            else:
                                                get_wh = check_out_ttf - check_in_ttf

                                    elif lcl_check_in <= var_duty_from:
                                        if lcl_check_out >= var_duty_to:
                                            if calendar.hour_to < calendar.hour_from:
                                                get_wh = (calendar.hour_to + 24.0) - calendar.hour_from
                                            else:
                                                get_wh = calendar.hour_to - calendar.hour_from
                                        else:

                                            if lcl_check_out.date() == var_duty_to.date():
                                                get_wh = (check_out_ttf + 24.0) - calendar.hour_from

                                            else:
                                                get_wh = check_out_ttf - calendar.hour_from

                                    if get_wh > 0 and diff > 0:
                                        get_wh = get_wh - diff
                                    if get_wh > 0:
                                        diff_out_in += get_wh

                                    if grace_period:
                                        if var_duty_from.date() != var_duty_to.date():
                                            if lcl_check_in.date() == var_duty_from.date():
                                                if round(grace_period, 2) >= round((check_in_ttf - float_duty_hr_from),
                                                                                   2) and check_in_ttf > float_duty_hr_from:
                                                    diff_out_in += (check_in_ttf - float_duty_hr_from)
                                            else:
                                                if round(grace_period, 2) >= round(
                                                        ((check_in_ttf + 24.0) - float_duty_hr_from), 2) and (
                                                        check_in_ttf + 24.0) > float_duty_hr_from:
                                                    diff_out_in += ((check_in_ttf + 24.0) - float_duty_hr_from)
                                        else:
                                            if round(grace_period, 2) >= round((check_in_ttf - float_duty_hr_from),
                                                                               2) and check_in_ttf > float_duty_hr_from:
                                                diff_out_in += (check_in_ttf - float_duty_hr_from)

                                    if sched_hours > 0:
                                        if diff_out_in >= sched_hours:
                                            diff_out_in = sched_hours

                        elif work_type == 'range':
                            lcl_check_in = str(lcl_check_in)
                            lcl_check_out = str(lcl_check_out)
                            if get_check_in >= duty_hr_from or get_check_out >= duty_hr_from:

                                """Start: Get Excluded Hours"""

                                if lcl_check_in <= exc_hr_from:
                                    if lcl_check_out >= exc_hr_to:
                                        diff = calendar.exc_hr_to - calendar.exc_hr_from
                                    if lcl_check_out < exc_hr_to:
                                        diff = check_out_ttf - calendar.exc_hr_from
                                elif lcl_check_in > exc_hr_from:
                                    if lcl_check_out >= exc_hr_to:
                                        diff = calendar.exc_hr_to - check_in_ttf
                                    elif lcl_check_out < exc_hr_to:
                                        diff = check_out_ttf - check_in_ttf

                                """End: Get Excluded Hours"""

                                """Start: Get Worked Hours"""

                                if get_check_in >= duty_hr_from:
                                    if get_check_out <= duty_hr_to:
                                        diff_out_in = check_out_ttf - check_in_ttf
                                    if get_check_out > duty_hr_to:
                                        diff_out_in = calendar.hour_to - check_in_ttf

                                if get_check_in < duty_hr_from:
                                    if get_check_out <= duty_hr_to:
                                        diff_out_in = check_out_ttf - calendar.hour_from
                                    if get_check_out > duty_hr_to:
                                        diff_out_in = calendar.hour_to - calendar.hour_from
                                if diff >= 0:
                                    diff_out_in = diff_out_in - diff

                                if grace_period:
                                    if round(grace_period, 2) >= round((check_in_ttf - float_duty_hr_from),
                                                                       2) and check_in_ttf > float_duty_hr_from:
                                        diff_out_in += (check_in_ttf - float_duty_hr_from)

                                """End: Get Worked Hours"""
                        elif work_type == 'core_plus':
                            get_wh = total_wh
                            diff_out_in = get_wh
                            core_worked = get_wh
                        elif work_type == 'core':
                            flex_start = calendar.hour_from
                            flex_end = calendar.hour_to
                            core_hours = flex_end - flex_start

                            if check_out_dte > check_in_dte:
                                get_wh = flex_end - check_in_ttf
                                diff_out_in = get_wh
                                core_worked = get_wh


                            else:
                                if get_check_in <= duty_hr_from and get_check_out >= duty_hr_to:
                                    get_wh = check_out_ttf - check_in_ttf
                                    diff_out_in = sched_hours

                                elif get_check_in <= duty_hr_from and get_check_out < duty_hr_to:
                                    get_wh = check_out_ttf - calendar.hour_from
                                    if check_out_ttf >= flex_end:
                                        core_worked = flex_end - flex_start
                                    elif check_in_ttf < flex_end:
                                        core_worked = check_out_ttf - flex_start
                                elif get_check_in > duty_hr_from and get_check_out >= duty_hr_to:
                                    get_wh = calendar.hour_to - check_in_ttf
                                    if check_in_ttf <= flex_start:
                                        core_worked = flex_end - flex_start
                                    elif check_in_ttf > flex_start:
                                        core_worked = flex_end - check_in_ttf

                                elif get_check_in > duty_hr_from and get_check_out < duty_hr_to:
                                    get_wh = check_out_ttf - check_in_ttf
                                    if check_in_ttf <= flex_start and check_out_ttf >= flex_end:
                                        core_worked = flex_end - flex_start
                                    elif check_in_ttf <= flex_start and check_out_ttf < flex_end:
                                        core_worked = check_out_ttf - flex_start
                                    elif check_in_ttf > flex_start and check_out_ttf > flex_end:
                                        core_worked = flex_end - check_in_ttf
                                    elif check_in_ttf > flex_start and check_out_ttf < flex_end:
                                        core_worked = check_out_ttf - check_in_ttf

                                else:
                                    get_wh = check_out_ttf - check_in_ttf
                                    core_worked = get_wh

                            if core_worked < core_hours:
                                diff_out_in = core_worked
                            else:
                                diff_out_in = get_wh

                            if grace_period:
                                if round(grace_period) >= round((check_in_ttf - float_duty_hr_from),
                                                                2) and check_in_ttf > float_duty_hr_from:
                                    diff_out_in += (check_in_ttf - float_duty_hr_from)
                        elif work_type == 'shift':
                            if var_duty_from.date() == var_duty_to.date():

                                if lcl_check_in <= var_exc_hr_from:
                                    if lcl_check_out >= var_exc_hr_to:
                                        diff = calendar.exc_hr_to - calendar.exc_hr_from
                                    if lcl_check_out < var_exc_hr_to:
                                        diff = check_out_ttf - calendar.exc_hr_from
                                elif lcl_check_in > var_exc_hr_from:
                                    if lcl_check_out >= var_exc_hr_to:
                                        diff = calendar.exc_hr_to - check_in_ttf
                                    elif lcl_check_out < var_exc_hr_to:
                                        diff = check_out_ttf - check_in_ttf

                                if lcl_check_in <= var_duty_from and lcl_check_out >= var_duty_to:
                                    get_wh = calendar.hour_to - calendar.hour_from

                                elif lcl_check_in > var_duty_from:
                                    if lcl_check_out >= var_duty_to:
                                        get_wh = calendar.hour_to - check_in_ttf
                                    else:
                                        get_wh = check_out_ttf - check_in_ttf

                                elif lcl_check_in <= var_duty_from:

                                    if lcl_check_out >= var_duty_to:
                                        get_wh = calendar.hour_to - calendar.hour_from
                                    else:
                                        get_wh = check_out_ttf - calendar.hour_from

                                if get_wh > 0 and diff > 0:
                                    get_wh = get_wh - diff
                                if get_wh > 0:
                                    diff_out_in += get_wh
                            else:
                                if lcl_check_in <= var_exc_hr_from:
                                    if lcl_check_out >= var_exc_hr_to:
                                        if calendar.exc_hr_to < calendar.exc_hr_from:
                                            diff = (calendar.exc_hr_to + 24.0) - calendar.exc_hr_from
                                        else:
                                            diff = calendar.exc_hr_to - calendar.exc_hr_from

                                    if lcl_check_out < var_exc_hr_to:
                                        if var_duty_to.date() == lcl_check_out.date():
                                            if var_duty_to.date() == var_exc_hr_from.date():
                                                diff = check_out_ttf - calendar.exc_hr_from
                                            else:
                                                diff = (check_out_ttf + 24.0) - calendar.exc_hr_from
                                        else:
                                            if var_duty_to.date() == var_exc_hr_from.date():
                                                diff = check_out_ttf - (calendar.exc_hr_from + 24.0)
                                            else:
                                                diff = check_out_ttf - calendar.exc_hr_from


                                elif lcl_check_in > var_exc_hr_from:
                                    if lcl_check_out >= var_exc_hr_to:
                                        if var_exc_hr_to.date() == var_duty_to.date() and lcl_check_in.date() == var_duty_to.date():
                                            diff = calendar.exc_hr_to - check_in_ttf
                                        elif var_exc_hr_to.date() == var_duty_to.date():
                                            diff = (calendar.exc_hr_to + 24.0) - check_in_ttf
                                        elif lcl_check_in.date() == var_duty_to.date():
                                            diff = calendar.exc_hr_to - (check_in_ttf + 24.0)
                                        else:
                                            diff = calendar.exc_hr_to - check_in_ttf

                                    elif lcl_check_out < var_exc_hr_to:
                                        if lcl_check_out.date() == var_duty_to.date():
                                            diff = (check_out_ttf + 24.0) - check_in_ttf
                                        elif lcl_check_in.date() == var_duty_to.date():
                                            diff = check_out_ttf - (check_in_ttf + 24.0)
                                        else:
                                            diff = check_out_ttf - check_in_ttf

                                if lcl_check_in <= var_duty_from and lcl_check_out >= var_duty_to:
                                    if calendar.hour_to < calendar.hour_from:
                                        get_wh = (calendar.hour_to + 24.0) - calendar.hour_from
                                    else:
                                        get_wh = calendar.hour_to - calendar.hour_from

                                elif lcl_check_in > var_duty_from:
                                    if lcl_check_out >= var_duty_to:
                                        if lcl_check_in.date() == var_duty_to.date() and var_exc_hr_to.date() == var_duty_to.date():
                                            get_wh = calendar.hour_to - check_in_ttf
                                        elif lcl_check_in.date() == var_duty_to.date():
                                            get_wh = calendar.hour_to - (check_in_ttf + 24.0)
                                        elif var_exc_hr_to.date() == var_duty_to.date():
                                            get_wh = (calendar.hour_to + 24.0) - check_in_ttf
                                        else:
                                            get_wh = (calendar.hour_to + 24.0) - check_in_ttf
                                    else:
                                        if lcl_check_out.date() == var_duty_to.date() and lcl_check_in.date() == var_duty_to.date():
                                            get_wh = check_out_ttf - check_in_ttf
                                        elif lcl_check_out.date() == var_duty_to.date():
                                            get_wh = (check_out_ttf + 24.0) - check_in_ttf
                                        elif lcl_check_in.date() == var_duty_to.date():
                                            get_wh = check_out_ttf - (check_in_ttf + 24.0)
                                        else:
                                            get_wh = check_out_ttf - check_in_ttf

                                elif lcl_check_in <= var_duty_from:
                                    if lcl_check_out >= var_duty_to:
                                        if calendar.hour_to < calendar.hour_from:
                                            get_wh = (calendar.hour_to + 24.0) - calendar.hour_from
                                        else:
                                            get_wh = calendar.hour_to - calendar.hour_from
                                    else:
                                        if lcl_check_out.date() == var_duty_to.date():
                                            get_wh = (check_out_ttf + 24.0) - calendar.hour_from
                                        else:
                                            get_wh = check_out_ttf - calendar.hour_from

                                if get_wh > 0 and diff > 0:
                                    get_wh = get_wh - diff
                                if get_wh > 0:
                                    diff_out_in += get_wh

                            # wew = utf_var_check_in
                            if grace_period:
                                if var_duty_from.date() != var_duty_to.date():
                                    if lcl_check_in.date() == var_duty_from.date():
                                        if grace_period > (
                                                check_in_ttf - float_duty_hr_from) and check_in_ttf > float_duty_hr_from:
                                            diff_out_in += (check_in_ttf - float_duty_hr_from)
                                    else:
                                        if grace_period > ((check_in_ttf + 24.0) - float_duty_hr_from) and (
                                                check_in_ttf + 24.0) > float_duty_hr_from:
                                            diff_out_in += ((check_in_ttf + 24.0) - float_duty_hr_from)
                                else:
                                    if grace_period > (
                                            check_in_ttf - float_duty_hr_from) and check_in_ttf > float_duty_hr_from:
                                        diff_out_in += (check_in_ttf - float_duty_hr_from)

                        
                        if sched_hours > 0:
                            if work_type not in ['core', 'core_plus']:
                                if diff_out_in >= sched_hours:
                                    diff_out_in = sched_hours

                if work_type == 'open':
                    if not opentime_weekdays:
                        diff_out_in = check_out_ttf - check_in_ttf

                actual_wh = actual_wh + diff_out_in
                # print 'date_line',date_line , 'actual_wh',actual_wh
                for contract in self.contract_id:
                    if contract.absence_policy_id:
                        abs_other = contract.absence_policy_id.mapped('line_ids').filtered(
                            lambda line: line.use_other == True)
                        if abs_other:
                            hr_from = abs_other.hour_from
                            hr_to = abs_other.hour_to
                            equivalent = abs_other.equivalent_hour
                            if actual_wh >= hr_from and actual_wh <= hr_to:
                                actual_wh = equivalent
        else:
            if work_type == 'shift':
                if holiday:
                    for hol in holiday:
                        abs_holiday = contract_id.absence_policy_id.mapped('line_ids').filtered(
                            lambda line: line.use_holiday == True and line.holiday_id.id == hol.holiday_type.id)

                        if abs_holiday.type == 'unpaid':
                            ot_det = self.env['hr.overtime.line'].search([('overtime_id.employee_id', '=', employee_id),
                                                                         ('overtime_id.state', '=', 'approve')]).filtered(
                                lambda det: det.overtime_id.start_date == get_date and det.overtime_id.end_date == get_date and det.is_auto == False)

                            if ot_det:
                                for line in ot_det:
                                    actual_wh = line.numofhours
                            else:

                                ot_det = self.env['hr.overtime.line'].search(
                                    [('overtime_id.state', '=', 'approve')]).filtered(lambda
                                                                                          det: employee_id in det.overtime_id.employee_ids.ids and det.overtime_id.start_date == get_date
                                                                                               and det.overtime_id.end_date == get_date and det.is_auto == False)
                                for line in ot_det:
                                    actual_wh = line.numofhours

                if leaves:
                    for leave in leaves:

                        abs_leave = contract_id.absence_policy_id.mapped('line_ids').filtered(
                            lambda line: line.use_leave == True and line.holiday_status_id.id == leave[
                                0].holiday_status_id.id)

                        lv_day_before = ''
                        lv_day_after = ''
                        if abs_leave:
                            lv_day_before = abs_leave.day_before
                            lv_day_after = abs_leave.day_after

                        timesheet_remarks = ''
                        if lv_day_before:
                            restday = True
                            counter = 1
                            while restday:
                                timesheet_date = date_line - timedelta(days=counter)
                                timesheet_summary = self.env['hr_timesheet.summary'].search(
                                    [('date', '=', timesheet_date.strftime('%Y-%m-%d')),
                                     ('employee_id', '=', self.employee_id.id)])
                                timesheet_remarks = timesheet_summary.remarks
                                timesheet_holiday = self.get_holiday(timesheet_date)
                                timesheet_leave = self.count_leaves(timesheet_date, self.employee_id.id, period)

                                if (
                                        timesheet_summary.duty_hours != 0 or timesheet_holiday or timesheet_leave) and work_type != 'open':
                                    restday = False
                                elif work_type == 'open' and timesheet_summary.actual_worked_hours > 0 and timesheet_summary.remarks:
                                    restday = False
                                counter += 1

                        if timesheet_remarks == 'ABS' and lv_day_before:
                            leave[0].sudo().write({'state': 'refuse'})
                else:
                    if not holiday and (dh and duty_hours['calendar_atndnce_ids']):
                        date_today = date.today()
                        if date_line.date() <= date_today:
                            restday = True
                            counter = 1
                            timesheet_leave = ''
                            timesheet_remarks = ''
                            while restday:
                                timesheet_date = date_line - timedelta(days=counter)
                                timesheet_summary = self.env['hr_timesheet.summary'].search(
                                    [('date', '=', timesheet_date.strftime('%Y-%m-%d')),
                                     ('employee_id', '=', self.employee_id.id)])
                                timesheet_remarks = timesheet_summary.remarks
                                timesheet_holiday = self.get_holiday(timesheet_date)
                                timesheet_leave = self.count_leaves(timesheet_date, self.employee_id.id, period)

                                if (
                                        timesheet_summary.duty_hours != 0 or timesheet_holiday or timesheet_leave) and work_type != 'open':
                                    restday = False
                                elif work_type == 'open' and timesheet_summary.actual_worked_hours > 0 and timesheet_summary.remarks:
                                    restday = False
                                counter += 1

                            lv_day_after = ''
                            for leave in timesheet_leave:
                                abs_leave = contract_id.absence_policy_id.mapped('line_ids').filtered(
                                    lambda line: line.use_leave == True and line.holiday_status_id.id == leave[
                                        0].holiday_status_id.id)

                                if abs_leave:
                                    lv_day_after = abs_leave.day_after

                                if timesheet_leave and lv_day_after:
                                    leave[0].sudo().write({'state': 'refuse'})

        rec_ctr += 1
        # print 'actual_wh',actual_wh
        vals = {'check_in': check_in,
                'check_out': check_out,
                # Added codes for monthly grace period
                'late_in': late_in,
                # Added codes for monthly grace period - END
                'attendance_ids': attendance_ids,
                'actual_wh': actual_wh,
                'get_total_wh': get_total_wh,
                'total_wh': total_wh,
                'core_worked': core_worked,
                'leaves': leaves,
                }

        return vals
    
    @api.multi
    def get_remarks(self, date_line, work_type,
                    leaves, diff, actual_wh, get_wh, get_actual_ot, dh, wh, late, get_ut, holiday):
        attendance_ids = get_wh['attendance_ids']

        remark = ''
        cur_date = datetime.strptime(datetime.today().strftime('%Y-%m-%d'), '%Y-%m-%d')
        get_date = datetime.strptime(date_line.strftime('%Y-%m-%d'), '%Y-%m-%d')
        leave_remark = ''
        hol_code = ''
        leave_code_rem = 'LEA'
        if leaves:
            get_leave = leaves[-1][0][-1]
            leave_code = get_leave.holiday_status_id.code or ''
            if leave_code:
                leave_code_rem = leave_code

        if get_date <= cur_date:
            if holiday:
                for rec in holiday:
                    if rec.holiday_type.code and rec:
                        if hol_code:
                            hol_code = hol_code + '/' + rec.holiday_type.code
                        else:
                            hol_code = rec.holiday_type.code
                    else:
                        hol_code = ''
                if get_actual_ot > 0:
                    remark = 'HOL-' + hol_code + ' OT'
                else:
                    remark = 'HOL-' + hol_code

            elif wh > 0 or actual_wh > 0:
                if leaves:
                    if 'LOA' in leave_code:
                        if leaves[-1][0].number_of_days_temp < 1:
                            leave_remark = leave_code_rem + '-HD/ABS'
                        else:
                            leave_remark = leave_code_rem + '/ABS'
                        if get_actual_ot > 0:
                            remark = leave_remark + '/' + 'OT'

                    elif dh in range(0, 8):
                        if leaves[-1][0].req_type == 'hours':
                            leave_remark = leave_code_rem + '-HRS'
                        else:
                            leave_remark = leave_code_rem + '-HD'

                    elif leaves[-1][0].req_type == 'hours':
                        leave_remark = leave_code_rem + '-HRS'
                    elif leaves[-1][0].req_type in ['half_am','half_pm']:
                        leave_remark = leave_code_rem + '-HD'
                        if dh > 0 and actual_wh <= 0:
                            remark = 'ABS'
                    else:
                        leave_remark = leave_code_rem
                        if dh > 0 and actual_wh <= 0:
                            remark = 'ABS'

                if late > 0 and get_ut > 0:
                    if get_ut > 0:
                        remark = 'LATE/UT'
                        if leaves:
                            remark = remark + '/' + leave_remark
                elif late > 0 and get_ut <= 0:
                    remark = 'LATE'
                    if leaves:
                        remark = remark + '/' + leave_remark
                    if get_actual_ot > 0:
                        remark = remark + '/' + 'OT'

                elif get_ut > 0 and late <= 0:
                    remark = 'UT'
                    if leaves:
                        remark = remark + '/' + leave_remark
                elif diff >= 0:
                    if dh == 0 and work_type != 'open':
                        if get_actual_ot > 0:
                            remark = 'RD OT'
                        else:
                            remark = 'RD'
                    elif leaves:
                        remark = leave_remark
                        if get_actual_ot > 0:
                            remark = leave_remark + '/' + 'OT'
                    elif get_actual_ot > 0:
                        remark = 'OT'

                elif leaves:
                    remark = leave_remark

            elif get_actual_ot > 0:
                if leaves:
                    remark = 'OT' + '/' + leave_code_rem
                elif dh == 0 and work_type != 'open':
                    remark = 'RD OT'
                elif dh != 0 and actual_wh == 0 and work_type != 'open':
                    remark = 'OT/ABS'
                else:
                    remark = 'OT'

            elif leaves:
                remark = leave_code_rem
                leave_type_id = leaves[-1][0][-1].holiday_status_id.id
                unpaid_holiday = self.contract_id.policy_id.absence_policy_ids.line_ids.filtered(
                    lambda rec: rec.holiday_status_id.id == leave_type_id and rec.type == 'unpaid')

                if dh > 0 and actual_wh == 0 and not unpaid_holiday:
                    remark = remark + '/ABS'


            elif dh <= 0 and work_type != 'open':
                remark = ''

            elif attendance_ids:
                for attndnce in attendance_ids:
                    if attndnce.check_in and not attndnce.check_out:
                        remark = 'NO CO'
                    elif attndnce.check_in and ('NO CO' in get_wh['check_out']):
                        remark = 'NO CO'
                    elif not attndnce.check_in and attndnce.check_out:
                        remark = 'NO CI'

            elif dh > 0 and actual_wh <= 0 and work_type not in ['core', 'core_plus'] and work_type != 'daily':
                remark = 'ABS'
            # print(dh,actual_wh, work_type)
        return remark
    
    @api.multi
    def calculate_duty_hours(self, contract_id, date_from, period):
        contract_obj = self.env['hr.contract']
        calendar_obj = self.env['resource.calendar']
        emp_id = self.employee_id.id
        duty_hours = 0.0
        contract_ids = contract_id

        for contract in contract_ids:
            ctx = dict(self.env.context).copy()
            ctx.update(period)
            work_type = contract.working_hours.work_type
            # flexi_type = contract.working_hours.flexi_type
            opentime_weekdays = contract.working_hours.opentime_weekdays
            calendar_id = contract.working_hours.id
            dh = 0
            if work_type == 'weekly' or work_type == 'range' or opentime_weekdays:
                dayweek = date_from.weekday()
                cal_att_ids = self.env['resource.calendar.attendance'].search(
                    [('calendar_id', '=', calendar_id), ('dayofweek', '=', dayweek)])
                for cal_att in cal_att_ids:
                    dh += cal_att.sched_hours

            elif work_type in ['daily','shift','core','core_plus']:
                if work_type == 'shift':
                    cal_att_ids = shift_calendar_ids(self, date_from, contract_id)
                    for cal in cal_att_ids:
                        # if calendar_atndnce_ids:
                        dh += cal.shift_id.sched_hours
                        # print 'dh',dh
                else:
                    cal_att_ids = self.env['resource.calendar.attendance'].search([('calendar_id', '=', calendar_id)])
                    for cal_att in cal_att_ids:
                        dh += cal_att.sched_hours
            else:
                dh = calendar_obj.get_working_hours_of_date(start_dt=date_from, resource_id=self.employee_id.id)

            leaves = self.count_leaves(date_from, self.employee_id.id, period)
            holiday = self.get_holiday(date_from)

            if not holiday:
                is_loa = False
                if leaves:
                    if contract.absence_policy_id:
                        abs_awol = contract.absence_policy_id.mapped('line_ids').filtered(
                            lambda line: line.use_awol == True)
                        if abs_awol:
                            for awol in abs_awol:
                                leave_id = awol.holiday_status_id
                                if leaves[-1][0]:
                                    leave_req_id = leaves[-1][0].holiday_status_id
                                    if leave_id == leave_req_id:
                                        is_loa = True

                if not leaves or is_loa:
                    if not dh:
                        dh = 0.00
                    duty_hours += dh
                else:
                    if leaves[-1] and leaves[-1][-1]:
                        if float(leaves[-1][-1]) == (-0.5) and leaves[-1][-4].req_type != 'hours':
                            duty_hours += dh / 2
                        elif leaves[-1][-4].req_type in ['half_am','half_pm','hours']:
                            duty_hours += dh + leaves[-1][-1]

        return duty_hours
        
    @api.onchange('contract_id','date_from','date_to')
    def _onchange_timesheet_period_check_contract_duration(self):
        for record in self:
            if record.contract_id:
                if record.date_from:
                    if record.contract_id.date_start:
                        if record.contract_id.date_start > record.date_from:
                            raise UserError(_('Timesheet Period is not within the contract duration!'))
                if record.date_to:
                    if record.contract_id.date_end:
                        if record.contract_id.date_end < record.date_to:
                            raise UserError(_('Timesheet Period is not within the contract duration!'))

def shift_calendar_ids(self, date_from, contract):
    calendar_atndnce_ids = []
    dh = 0
    self.env.cr.execute(
        "SELECT work_plan_id from work_plan_employees where employee_id = \'%s\'" % self.employee_id.id)
    emp_wrk_plan_id = self.env.cr.fetchall()
    ewp = []
    for e in emp_wrk_plan_id:
        ewp.append(e[0])

    is_ind = self.env['hr.work.plan'].search([('id', 'in', ewp), ('is_individual', '=', True)])
    if is_ind:
        for i in is_ind:
            calendar_atndnce_ids = self.env['hr.work.plan.line'].search(
                [('plan_id', '=', i.id), ('date_from', '=', str(date_from.date()))])
            if calendar_atndnce_ids:
                break
    else:
        work_plan_id = self.env['hr.work.plan'].search(
            [('partner_id', '=', contract.partner_id.id), ('is_individual', '=', False)])
        for w in work_plan_id:
            calendar_atndnce_ids = self.env['hr.work.plan.line'].search(
                [('plan_id', '=', w.id), ('date_from', '=', str(date_from.date()))])
            if calendar_atndnce_ids:
                break

    return calendar_atndnce_ids