import base64
import io

import pytz
from odoo import models, fields, api, modules
from datetime import date, datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.addons.report_xlsx.report.report_xlsx import ReportXlsx
from xlsxwriter.utility import xl_rowcol_to_cell, xl_col_to_name


class TimesheetExcelReport(models.Model):
    _inherit = 'hr_timesheet_sheet.sheet'

    def export_xls(self):
        context = self._context
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'res.partner'
        datas['form'] = self.read()[0]
        for field in datas['form'].keys():
            if isinstance(datas['form'][field], tuple):
                datas['form'][field] = datas['form'][field][0]
        if context.get('xls_export'):
            return {'type': 'ir.actions.report.xml',
                    'report_name': 'true_move.etsi_timesheet.hr_timesheet_sheet_sheet.xlsx',
                    'datas': datas,
                    'name': 'Partners'
                    }

class TimesheetXlsx(ReportXlsx):
    def generate_xlsx_report(self, workbook, data, partners):
        long_month = datetime.strptime(partners.date_from, '%Y-%m-%d').strftime('%B')
        date_date_from = datetime.strptime(partners.date_from, '%Y-%m-%d').strftime('%d')
        date_date_to = datetime.strptime(partners.date_to, '%Y-%m-%d').strftime('%d')
        long_year = datetime.strptime(partners.date_to, '%Y-%m-%d').strftime('%Y')
        # print 'data', data
        # print 'workbook', workbook
        # print 'id', self.id
        # print 'partners', partners
        titles = workbook.add_format(
            {'font_size': 18, 'border': 2, 'align': 'center', 'bold': True, 'font_name': 'Arial', 'bg_color': '#C0C0C0'})
        signatures = workbook.add_format({'font_size': 10, 'top': True, 'font_name': 'Arial'})
        labels = workbook.add_format({'font_size': 10, 'font_name': 'Arial'})
        infos = workbook.add_format({'font_size': 10, 'font_name': 'Arial', 'bold': True})
        datas = workbook.add_format({'font_size': 10, 'font_name': 'Arial', 'border': 1, 'align': 'center', 'text_wrap': True, 'valign': 'vcenter'})
        datas_red = workbook.add_format({'font_size': 10, 'font_name': 'Arial', 'border': 1, 'align': 'center', 'color': 'red', 'valign': 'vcenter'})
        datas_wend = workbook.add_format({'font_size': 10, 'font_name': 'Arial', 'border': 1, 'align': 'center', 'bg_color': '#FEFF99', 'valign': 'vcenter'})
        datas_name = workbook.add_format(
            {'font_size': 10, 'font_name': 'Arial', 'align': 'left', 'text_wrap': True, 'bold': True,
             'valign': 'vcenter'})
        datas_value = workbook.add_format(
            {'font_size': 10, 'font_name': 'Arial', 'align': 'center', 'text_wrap': True, 'bold': True,
             'valign': 'vcenter'})
        column = workbook.add_format({'font_size': 10, 'font_name': 'Arial', 'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 2, 'text_wrap': True})
        column2 = workbook.add_format({'font_size': 10, 'font_name': 'Arial', 'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True})
        sheet = workbook.add_worksheet('DTR')
        sheet.set_landscape()
        sheet.set_margins(left=0.25, right=0.25, top=0.75, bottom=0.75)
        sheet.fit_to_pages(1, 1)

        image_path = modules.module.get_resource_path('true_move', 'reports', 'logo.png')
        sheet.insert_image('A1', image_path, )

        sheet.set_column('A:A', 19)     # DATE IN
        sheet.set_column('B:B', 12)     # START TIME
        sheet.set_column('C:C', 18)     # DATE OUT
        sheet.set_column('D:D', 12)     # END TIME
        sheet.set_column('E:E', 10)     # WORK HRS.
        sheet.set_column('F:F', 11)     # PROJECT
        # OVERTIME
        sheet.set_column('G:G', 19)     # START TIME
        sheet.set_column('H:H', 19)     # END TIME
        sheet.set_column('I:I', 10)     # OVERTIME HRS.
        sheet.set_column('J:J', 10)     # CHARGE TO CC
        sheet.set_column('K:K', 25)     # PURPOSE
        sheet.set_column('L:L', 9)      # TOTAL HRS.

        sheet.write('A6', 'Timesheet Period : ', labels); sheet.write('B6', '%s to %s'%(partners.date_from, partners.date_to), infos)

        sheet.write('A8', 'Name : ', labels); sheet.write('B8', partners.employee_id.name_related, infos)
        sheet.write('A9', 'Employment Classification: ', labels); sheet.write('B9', partners.employee_id.emp_categ_id.name, infos)
        sheet.write('A10', 'Official Working Hour :', labels); sheet.write('B10', partners.working_hours.name, infos)

        sheet.write('H8', 'Company: ', labels); sheet.write('I8', partners.employee_id.address_id.name, infos)

        sheet.write('H9', 'Domain: ', labels); sheet.write('I9', partners.employee_id.domain_id.name, infos)
        sheet.write('H10', 'Department: ', labels); sheet.write('I10', partners.employee_id.department_id.name, infos)

        sheet.merge_range('A14:F14', 'Regular Hours', titles); sheet.merge_range('G14:L14', 'Overtime Request', titles)
        sheet.set_row(14, 5)
        sheet.set_row(15, 25)
        sheet.merge_range('A16:A17', 'DATE IN', column2);  sheet.merge_range('B16:B17', 'START TIME', column2)
        sheet.merge_range('C16:C17', 'DATE OUT', column2); sheet.merge_range('D16:D17', 'END TIME', column2)
        sheet.merge_range('E16:E17', 'WORK HRS.', column2); sheet.merge_range('F16:F17', 'REMARKS', column2)
        sheet.merge_range('G16:G17', 'START TIME', column2); sheet.merge_range('H16:H17', 'END TIME', column2)
        sheet.merge_range('I16:I17', 'OVERTIME HRS.', column2); sheet.merge_range('J16:J17', 'CHARGE TO CC', column2)
        sheet.merge_range('K16:K17', 'PURPOSE', column2); sheet.merge_range('L16:L17', 'TOTAL HRS.', column2)

        date_from = datetime.strptime(partners.date_from, '%Y-%m-%d') + timedelta(days=-1)
        _date_from = date_from.strftime('%Y-%m-%d')
        date_to = datetime.strptime(partners.date_to, '%Y-%m-%d') + timedelta(days=1)
        _date_to = date_to.strftime('%Y-%m-%d')

        emp_id = self.env['hr.employee'].search([('id', '=', partners.employee_id.id)])
        timesheet_sum = self.env['hr_timesheet.summary'].search([('employee_id', '=', emp_id.id),
                                                                 ('date', '>=', partners.date_from),
                                                                 ('date', '<=', partners.date_to)], order='date ASC')
        attendance = self.env['hr.attendance'].search([('employee_id', '=', emp_id.id),
                                                       ('check_in', '>=', _date_from),
                                                       ('check_out', '<=', _date_to)], order='check_in ASC')
        new_attn = []
        for time_in in attendance:
            df = DEFAULT_SERVER_DATETIME_FORMAT
            user_tz = self.env.user.tz or str(pytz.utc)
            local = pytz.timezone(user_tz)

            check_in = datetime.strftime(
                pytz.utc.localize(datetime.strptime(time_in.check_in, df)).astimezone(local),
                "%Y-%m-%d %H:%M:%S")
            check_out = datetime.strftime(
                pytz.utc.localize(datetime.strptime(time_in.check_out, df)).astimezone(local),
                "%Y-%m-%d %H:%M:%S")

            check_in_date = datetime.strptime(check_in, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
            check_in_time = datetime.strptime(check_in, '%Y-%m-%d %H:%M:%S').strftime('%I:%M %p')
            check_out_time = datetime.strptime(check_out, '%Y-%m-%d %H:%M:%S').strftime('%I:%M %p')

            rec = {
                'check_in_date': check_in_date,
                'check_out_date': check_out_date,
                'check_in_time': check_in_time,
                'check_out_time': check_out_time
            }
            new_attn.append(rec)

        row_date_in = 17
        row_time_in = 17
        row_time_out = 17
        row_actual_worked_hours = 17
        row_project = 17
        row_ot_in = 17
        row_ot_out = 17
        row_ot_hrs = 17
        row_remarks = 17
        row_tot_hrs = 17
        row_signature = row_date_in
        # DATE IN & DATE OUT
        for rec in timesheet_sum:
            date_in = datetime.strptime(rec.date, '%Y-%m-%d').strftime('%m-%d-%Y %a')
            if 'Sat' in date_in or 'Sun' in date_in:
                sheet.write('A' + str(row_date_in), date_in, datas_wend)
                sheet.write('C' + str(row_date_in), date_in, datas_wend)
            else:
                sheet.write('A' + str(row_date_in), date_in, datas)
                sheet.write('C' + str(row_date_in), date_in, datas)
            row_date_in += 1
        # /DATE IN & DATE OUT

            # CHECK-IN & CHECK-OUT TIME
            current_attn = filter(lambda attn: attn['check_in_date'] == rec.date, new_attn)
            if current_attn:
                for res in current_attn:
                    sheet.write('B' + str(row_time_in), res['check_in_time'], datas)
                    sheet.write('D' + str(row_time_in), res['check_out_time'], datas)
                    row_time_in += 1
                    row_time_out += 1
            else:
                sheet.write('B' + str(row_time_in), '', datas)
                sheet.write('D' + str(row_time_in), '', datas)
                row_time_in += 1
                row_time_out += 1
            # /CHECK-IN & CHECK-OUT TIME

            # WORKED HRS.
            if rec.actual_worked_hours == 0.00:
                sheet.write('E' + str(row_actual_worked_hours), '', datas)
                row_actual_worked_hours += 1
            else:
                if rec.actual_worked_hours < 8.00:
                    sheet.write('E' + str(row_actual_worked_hours), '{:0,.2f}'.format(rec.actual_worked_hours), datas_red)
                    row_actual_worked_hours += 1
                else:
                    sheet.write('E' + str(row_actual_worked_hours), '{:0,.2f}'.format(rec.actual_worked_hours), datas)
                    row_actual_worked_hours += 1
            # /WORKED HRS.

            # PROJECT & CHARGE TO CC
            sheet.write('F' + str(row_project), rec.remarks, datas)
            sheet.write('J' + str(row_project), '', datas)
            row_project += 1
            # /PROJECT & CHARGE TO CC

            # OT TIME IN AND OUT
            # hr_OT = self.env['hr.overtime'].search([('employee_id', '=', partners.employee_id.id), ('state', '=', 'approve'),
            #                                         ('start_date', '>=', rec.date), ('end_date', '<=', rec.date)], order = 'start_date ASC')
            hr_OT = self.env['hr.overtime'].search([('employee_id', '=', partners.employee_id.id), ('state', '=', 'approve')])
            hr_OT_det = hr_OT.mapped('overtime_det_ids')
            attendance_obj = self.env['hr.attendance']
            ot_ctr = 0
            ot_start_time = ''
            ot_end_time = ''
            ot_hrs = 0
            ot_line_ids = self.env['hr.overtime.line'].search([('overtime_id.state', '=', 'approve'),
                                                               ('overtime_id.employee_id', '=', partners.employee_id.id), ('start_date', '=', rec.date)])
            if ot_line_ids:
                for ot_line in ot_line_ids:
                    ot_in = ot_out = datetime.strptime(ot_line.start_date, '%Y-%m-%d').strftime('%m-%d-%Y')
                    # ot_out = datetime.strptime(ot_line_id.start_date, '%Y-%m-%d').strftime('%m-%d-%Y')
                    ftt_start_time = attendance_obj.float_time_convert(ot_line.start_time)
                    # get_start_time = datetime.strptime(ftt_start_time + ':00', "%H:%M:%S")
                    # ot_start_time = ot_in + ' ' + datetime.strftime(get_start_time, "%I:%M %p")
                    ot_start_time = ot_in + ' ' + ftt_start_time
                    ftt_end_time = attendance_obj.float_time_convert(ot_line.end_time)
                    # get_end_time = datetime.strptime(ftt_end_time + ':00', "%H:%M:%S")
                    get_end_time = datetime.strptime(ftt_end_time + ':00', "%H:%M:%S")
                    ot_end_time = ot_out + ' ' + ftt_end_time
                    if '12:00 AM' in ot_start_time or '12:00 AM' in ot_end_time:
                        ot_end_time = ""
                        ot_start_time = ""
                    sheet.write('G' + str(row_ot_in), ot_start_time, datas)
                    sheet.write('H' + str(row_ot_in), ot_end_time, datas)
                    sheet.write('K' + str(row_ot_in), ot_line.purpose, datas)
                    row_ot_in += 1
            else:
                sheet.write('G' + str(row_ot_in), '', datas)
                sheet.write('H' + str(row_ot_in), '', datas)
                sheet.write('K' + str(row_ot_in), '', datas)
                row_ot_in += 1

            # OVERTIME HRS.
            ot_hrs = ot_hrs + rec.actual_ot
            if ot_hrs == 0.00:
                sheet.write('I' + str(row_ot_hrs), '', datas)
                row_ot_hrs += 1
            else:
                sheet.write('I' + str(row_ot_hrs), '{:0,.2f}'.format(ot_hrs), datas)
                row_ot_hrs += 1
            # /OVERTIME HRS.

            # PURPOSE
            # if hr_OT_det:
            #     sheet.write('K' + str(row_remarks), hr_OT_det[0].purpose, datas)
            #     row_remarks += 1
            # else:
            #     sheet.write('K' + str(row_remarks), '', datas)
            #     row_remarks += 1

            # TOTAL HRS.
            act_total_hrs = rec.actual_ot + rec.actual_worked_hours
            sheet.write('L' + str(row_tot_hrs), '{:0,.2f}'.format(act_total_hrs), datas)
            row_tot_hrs += 1

        # TIMESHEET SUMMARY
        ut_hours = 0
        actual_ot = 0
        holiday_hours = 0
        abs_hours = 0
        leave_hours = 0
        late_hours = 0
        worked_hours = 0
        actual_worked_hours = 0

        summary_ids = self.env['hr_timesheet.summary'].search([('sheet_id', '=', partners.id)])
        for summary_id in summary_ids:
            ut_hours += summary_id.ut_hours
            actual_ot += summary_id.actual_ot
            holiday_hours += summary_id.holiday_hours
            abs_hours += summary_id.abs_hours
            leave_hours += summary_id.leave_hours
            late_hours += summary_id.late_hours
            worked_hours += summary_id.worked_hours
            actual_worked_hours += summary_id.actual_worked_hours

        timesheet_sum = [{'name': 'Total Undertime Hours: ', 'value': ut_hours},
                         {'name': 'Total Overtime Hours: ', 'value': actual_ot},
                         {'name': 'Total Holiday Hours: ', 'value': holiday_hours},
                         {'name': 'Total Absent Hours: ', 'value': abs_hours},
                         {'name': 'Total Leave Hours: ', 'value': leave_hours},
                         {'name': 'Total Late Hours: ', 'value': late_hours},
                         {'name': 'Total Actual Worked Hours: ', 'value': actual_worked_hours}]

        row_timesheet_sum = row_date_in
        k_column = xl_col_to_name(10)
        l_column = xl_col_to_name(11)
        sheet.write(k_column + str(row_timesheet_sum), '', datas_name)
        for rec in timesheet_sum:
            sheet.write(k_column + str(row_timesheet_sum+1), rec['name'], datas_name)
            sheet.write(l_column + str(row_timesheet_sum+1), str(rec['value']) if rec['value'] else '0.00', datas_value)
            row_timesheet_sum += 1

        nth_row_signature = row_timesheet_sum + 3
        nth_row_line = nth_row_signature + 2

        sheet.write('A' + str(nth_row_signature), 'Employee Signature:', signatures)
        sheet.write('A' + str(nth_row_line ), 'Date:___________', labels)
        sheet.write('C' + str(nth_row_signature), 'Immediate Supervisor:', signatures)
        sheet.write('C' + str(nth_row_line), 'Date:___________', labels)
        # sheet.merge_range('E' + str(nth_row_signature) + ':F' + str(nth_row_signature),
        #                   'WSI HR Head Signature:', signatures)
        # sheet.write('E' + str(nth_row_line), 'Date:___________', labels)
        # sheet.merge_range('H' + str(nth_row_signature) + ':I' + str(nth_row_signature),
        #                   'WSI General Manager Signature:', signatures)
        # sheet.write('H' + str(nth_row_line), 'Date:___________', labels)


TimesheetXlsx('report.true_move.etsi_timesheet.hr_timesheet_sheet_sheet.xlsx',
            'hr_timesheet_sheet.sheet')