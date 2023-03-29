from odoo import api, fields, models, _

class MembershipDataEntry(models.Model):
    _inherit = "hr.employee"

    gender = fields.Many2one('hr.gender')
    state = fields.Selection([
        ('draft','Draft'),
        ('fapproval','For Approval'),
        ('approved','Approved'),
        ('hold','Hold')
    ], string="Status", default="draft")

    # Personal Information
    fname = fields.Char('First name')
    mname = fields.Char('Middle name')
    lname = fields.Char('Last name')
    suffix = fields.Char('Suffix')
    res_address = fields.Char('Residential Address')
    place_of_birth = fields.Char('Place of Birth')
    home_tel_num = fields.Integer('Home Telephone Number')
    mobile_num = fields.Integer('Mobile number')
    name_of_spouse = fields.Char('Name of Spouse')
    email = fields.Char('Email Address')
    place_of_pms = fields.Char('Place of PMS')
    date_of_pms = fields.Date('Date of PMS')
    bank_name = fields.Many2one('res.bank')
    bank_acc_number = fields.Char('Bank account number')
    tin_no = fields.Char('TIN Number')
    sss_no = fields.Char('SSS Number')

    # Company Information
    emp_id = fields.Char('Employee ID No')
    payroll_group = fields.Many2one('wgcc.payroll.group', string='Payroll Group')
    office_tel_no = fields.Integer('Office Tel No')
    date_hired = fields.Date('Date Hired')
    date_resigned = fields.Date('Date Resigned from Company')
    previous_company = fields.Many2one('res.partner')
    salary = fields.Integer('Salary')
    principal_id_no = fields.Integer('Principal ID No')
    date_resigned_wgcc = fields.Date('Date Resigned from WGCC')

    # Beneficiary
    beneficiary = fields.One2many('hr.beneficiary', 'beneficiary_ids', string='Beneficiary')
    
    # Contact Information
    contactinfo = fields.One2many('hr.contact.info', 'contactInfo_ids', string='Contact Information')

    # Other Information
    date_of_membership = fields.Date("Date of Membership")
    first_deduct = fields.Char("First Deduction")
    membership_fee = fields.Char("Membership Fee")
    share_capital = fields.Char("Share Capital")
    savings_deposit = fields.Float("Savings Deposit")

    @api.onchange('fname','mname','lname','suffix')
    def fill_full_name(self):

        # Set variables to avoid false value
        lastname = ""
        firstname = ""
        middlename = ""
        suff = ""

        # If field has value
        if self.lname:
            lastname = self.lname
        if self.fname:
            firstname = self.fname
        if self.mname:
            middlename = self.mname
        if self.suffix:
            suff = self.suffix

        # Declaring the value
        self.update({"name": str(lastname) + ", " + str(firstname) + " " + str(middlename) + " " + str(suff)})

    # resource = self.env['resource.resource'].create({

    # })

                

class GenderLists(models.Model):
    _name = "hr.gender"
    _rec_name = "gender"

    gender = fields.Char('Gender')

class Beneficiary(models.Model):
    _name = "hr.beneficiary"

    beneficiary_ids = fields.Many2one('hr.employee')
    full_name = fields.Char('Full name')
    relationship = fields.Many2one('hr.relationship')
    date_of_birth = fields.Date('Date of Birth')

class ContactInfo(models.Model):
    _name = "hr.contact.info"

    contactInfo_ids = fields.Many2one('hr.employee')    
    contact_name = fields.Char('Name')
    contact_tel_no = fields.Char('Tel No.')
    contact_mobile_no = fields.Char('Mobile No.')
    contact_relationship = fields.Many2one('hr.relationship')
    contact_remarks = fields.Text('Remarks')

class RelationshipLists(models.Model):
    _name = "hr.relationship"
    _rec_name = "relationship"

    relationship = fields.Char('Relationship')
