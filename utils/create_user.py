import datetime

from kernel.models import *
from formula_one.models import *
from shell.models import *
from base_auth.models import User
from shell.constants import residences

from django_countries.data import COUNTRIES
from pseudoc.constants import CATEGORIES, DESIGNATION_DICT, DEPTS


def create_user(username, is_faculty, acad_data):
    """
    Function to create a user and person instancec for omniport
    :param username: Username of the user to be created
    :param is_faculty: True if user is a faculty, false otherwise
    :param acad_data: Data from the acad API, which we use to create user
    :return: user and person instance created
    """
    if is_faculty:
        uname = acad_data.get('IITREmailID', '').replace('iitr.ac.in', '')
        uname = uname.split('@')
        if len(uname) > 1:
            if uname[1] == '':
                username = uname[0]
            else:
                username = f'{uname[0]}f{uname[1].strip(".")}'

        if username is None or len(username) > 15:
            raise ValueError('Username could not be fetched')

    user, _ = User.objects.get_or_create(
        username=username,
    )
    person_object, new_person = Person.objects.get_or_create(
        user=user,
        full_name=acad_data['Name'].title(),
    )

    return user, person_object


def create_faculty(data, person_object):
    """
    Function to create faculty for a person
    :param data: data from ACAD API
    :param person_object: the person whose faculty role to define
    :return: faculty instance created
    """
    faculty = FacultyMember.objects.get_or_create(
        employee_id=int(data['EmployeeNo']),
        defaults={
            'content_object': Department.objects.get(
                code=DEPTS[data['DepartmentAlphaCode'].lower()]
            ),
            'start_date': datetime.datetime.now(),
            'person': person_object,
            'designation': DESIGNATION_DICT.get(
                data['Designation'].lower()
            ),
        }
    )

    return faculty


def create_student(data, person_object):
    """
    Function to create student for a person
    :param data: data from ACAD API
    :param person_object: the person whose student role to be defined
    :return: student instance created
    """

    sem_id = str(data['SemesterID'])
    student = Student(
        start_date=datetime.datetime.now(),
        person=person_object,
        enrolment_number=int(data['EnrollmentNo']),
        branch=Branch.objects.get(code=data['ProgramID']),
        current_year=int(sem_id[1]),
        current_semester=(int(sem_id[1]) - 1) * 2 + int(
            sem_id[2]) + 1
    )
    try:
        father = Person.objects.create(
            full_name=student['Fathersname'].title()
        )
        mother = Person.objects.create(
            full_name=student['MotherName'].title(),
        )
        person_object.parents.add(father)
        person_object.parents.add(mother)
        person_object.save()
    except:
        pass
    student.save()

    return student


def populate_location_info(location_information, details):
    """
    Function to populate the location info of a person based on ACAD API data
    :param location_information: location information instance
    :param details: data from ACAD API
    :return: True if successful, False otherwise
    """
    try:
        country_code = "IN"
        nationality = details.get('Nationality', '') or \
                      details.get('Pcountry', '') or ''
        for c, v in COUNTRIES.items():
            if v.lower() == nationality.lower():
                country_code = c
                break

        location_information.address = details.get(
            'PermanentAddress', ''
        ) or ''
        location_information.state = details.get('State', '') or ''
        location_information.city = details.get('City', '') or ''
        location_information.country = country_code

        location_information.save()

        return True
    except:
        return False


def populate_contact_info(contact_information, details):
    """
    Function to populate the contact info of a person based on ACAD API data
    :param contact_information: location information instance
    :param details: data from ACAD API
    :return: True if successful, False otherwise
    """
    try:
        contact_information.primary_phone_number = details.get(
            'Mobileno', None
        )
        contact_information.secondary_phone_number = details.get(
            'ContactNo', None
        )
        contact_information.email_address = details['EmailID']
        contact_information.institute_webmail_address = details.get(
            'PRIEMAIL',
            details['IITREmailID']
        )

        contact_information.save()
        return True
    except:
        return False


def populate_details(person_object, details):
    """
    One function which handles the creation and population of biological info,
    location info, contact info, residential and political info of a person
    :param person_object: person object for whom model instances to be created
    :param details: data from ACAD API
    :return: None
    """
    # --------------------------LocationInfo Creation--------------------------#
    try:
        # Default country = India

        location_information = LocationInformation.objects.create(
            entity=person_object
        )

        populate_location_info(location_information, details)

    except:
        pass
    # -------------------------------------------------------------------------#

    # --------------------------ContactInfo Creation---------------------------#
    try:
        contact_information = ContactInformation.objects.create(
            entity=person_object
        )
        populate_contact_info(contact_information, details)

    except:
        pass
    # -------------------------------------------------------------------------#

    # --------------------------PoliticalInfo Creation-------------------------#
    try:
        category_code = "oth"  # Default is 'other'
        country_code = "IN"
        try:
            category_code = CATEGORIES.get(details.get("Category", "other"),
                                           'oth')
            nationality = details.get('Nationality', '') or \
                          details.get('Pcountry', '') or ''
            for c, v in COUNTRIES.items():
                if v.lower() == nationality.lower():
                    country_code = c
                    break
        except:
            pass

        _ = PoliticalInformation.objects.create(
            person=person_object,
            nationality=country_code,
            religion=(details.get('Religion', "") or '').title(),
            reservation_category=category_code,
        )
    except:
        pass
    # -------------------------------------------------------------------------#

    # ---------------------------BiologicalInfo Creation-----------------------#
    try:

        all_blood_groups = ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-']

        # Default = 'O+'
        blood_group = (details.get("BloodGroup", 'O+') or 'O+').upper().\
            strip().replace(
            ' ', '')
        if blood_group not in all_blood_groups:
            blood_group = 'O+'

        _ = BiologicalInformation.objects.create(
            person=person_object,

            # If DoB is not found, mark today's date as Birth Date.
            date_of_birth=datetime.datetime.strptime(
                details["DateofBirth"], "%Y-%m-%dT%H:%M:%S"
            ).date() \
                if details.get("DateofBirth", False) else
            datetime.datetime.now().date(),

            blood_group=blood_group,

            # If gender is not found, mark default sex as male
            sex=details['Gender'].lower() \
                if details.get('Gender', False) else 'male',

            # If gender is not found, mark default gender as man
            gender='woman' \
                if (details.get('Gender', False)
                    and details['Gender'].lower().startswith('f')) \
                else 'man',

            # If gender is not found, mark default pronoun as 'he/his/him'
            pronoun='s' \
                if (details.get('Gender', False)
                    and details['Gender'].lower().startswith('f')) \
                else 'h',

            impairment='n'
        )
    except:
        pass
    # -------------------------------------------------------------------------#

    # ---------------------------FinancialInfo Creation------------------------#
    try:
        _ = FinancialInformation.objects.create(
            person=person_object,
        )
    except:
        pass
    # -------------------------------------------------------------------------#

    # ---------------------------ResidentialInfo Creation----------------------#
    try:
        # default bhawan as 'not a resident'
        bhawan_code = "nor"
        for rr in residences.RESIDENCES:
            if rr[1].lower() == details['Bhawan'].lower():
                bhawan_code = rr[0]
                break

        _ = ResidentialInformation.objects.create(
            person=person_object,
            residence=Residence.objects.get_or_create(code=bhawan_code)[0],
            room_number=details.get('RoomNo', "NIL")
        )
    except:
        pass
    # -------------------------------------------------------------------------#
