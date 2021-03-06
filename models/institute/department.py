from django.db import models

from kernel.models import AbstractDepartment
from shell.constants import departments


class Department(AbstractDepartment):
    """
    Make changes to AbstractDepartment to suit IIT Roorkee
    """

    code = models.CharField(
        max_length=7,
        unique=True,
        choices=departments.DEPARTMENTS,
    )

    @property
    def name(self):
        """
        Return the name of the department
        :return: the name of the department
        """

        return self.get_code_display()
