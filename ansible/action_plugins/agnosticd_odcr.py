#!/usr/bin/python

from __future__ import (absolute_import, division, print_function)
import datetime
import re
import pprint
import sys
import six
from ansible.errors import AnsibleError
from ansible.plugins.action import ActionBase
from ansible.utils.display import Display

import boto3
import botocore.exceptions

if sys.version_info < (2, 7):
    raise AnsibleError("agnosticd_odcr Ansible module require Python >= 2.7")

#pylint: disable=invalid-name
__metaclass__ = type
#pylint: enable=invalid-name

DOCUMENTATION = """
        action: agnosticd_odcr
        author: Guillaume Core <gucore@redhat.com>
        version_added: "2.9"
        short_description: Create AWS on-demand Capacity Reservations
        description:
            - Create reservations and return Regions / AZs / Ids
        options:
          _terms:
            description: reservations to create
            required: True
          ttl:
            description: The TTL to set in the reservations
            required: False
            type: int
            default: 1h
          distinct:
            description: If true, all the zones must be distinct. If false, do best-effort.
            required: False
            type: bool
            default: False

"""

EXAMPLES = """
- name: Create on-demand capacity reservations and save result
  agnosticd_odcr:
    reservations: "{{ agnosticd_aws_capacity_reservations }}"
    aws_access_key_id: "{{ aws_access_key_id }}"
    aws_secret_access_key: "{{ aws_secret_access_key }}"
    ttl: 1h
  register: r_odcr
"""

RETURN = """
_raw:
   description: Reservations
   type: list
"""

display = Display()
pp = pprint.PrettyPrinter(indent=2)

class InvalidDuration(Exception):
    """Exception for parse_duration."""

def parse_duration(time_str):
    """Parse duration (str) and return timedelta

    input examples:
      3d
      3h
      2s
      2h12m
      3d 12h 3m
      60s    (same as 60)

    default is second.  3600 = 1h

    Return False if the string doesn't match"""

    regex = re.compile(
        r'^((?P<days>\d+?)[dD])? *((?P<hours>\d+?)[hH])? *((?P<minutes>\d+?)m)? *((?P<seconds>\d+?)s?)?$'
    )

    if not time_str or not isinstance(time_str, six.string_types):
        raise InvalidDuration("'%s' is not a valid duration" %(time_str))
    parts = regex.match(time_str.strip())
    if not parts:
        raise InvalidDuration("'%s' is not a valid duration" %(time_str))
    parts = parts.groupdict()
    time_params = {}
    for (name, param) in iter(parts.items()):
        if param:
            time_params[name] = int(param)
    return datetime.timedelta(**time_params)

def translate_to_api_names(key_str):
    """Return the corresponding names to use with AWS Apis and python functions"""
    entries = {
        'instance_count': 'InstanceCount',
        'instance_platform': 'InstancePlatform',
        'instance_type': 'InstanceType',
        'instance_match_criteria': 'InstanceMatchCriteria',
        'tenancy': 'Tenancy',
    }

    if key_str in entries:
        return entries[key_str]

    raise AnsibleError("Key {} is not supported in a reservation.".format(key_str))


def tag_match(tags1, tags2):
    """All tags1 are in tags2"""
    for tag in tags1:
        if tag in tags2:
            continue

        return False

    return True

def check_response(response):
    """Check HTTPStatusCode"""
    try:
        if response['ResponseMetadata']['HTTPStatusCode'] != 200:
            display.error(pp.pformat(response))
            raise AnsibleError("Error requesting EC2 offerings.")
    except Exception as err:
        display.error(pp.pformat(response))
        six.raise_from(AnsibleError("Error requesting EC2 offerings."), err)


class ODCRFactory:
    """ActionModule class"""

    def get_azs(self, region):
        """Return all availability zones for a region"""

        if region not in self.availability_zones:
            response = self.clients[region].describe_availability_zones()

            self.availability_zones[region] = list(
                map(
                    lambda elem: elem['ZoneName'],
                    filter(
                        lambda elem: elem['State'] == 'available',
                        response['AvailabilityZones']
                    )
                )
            )

        return self.availability_zones[region]

    def filter_azs(self, region, instance_types):
        """Return the AZs with matching InstanceType offerings,
        given a list of instance types.
        """
        response = self.clients[region].describe_instance_type_offerings(
            LocationType='availability-zone',
            Filters=[
                {
                    'Name': 'instance-type',
                    'Values': list(instance_types),
                },
            ],
        )

        check_response(response)

        display.vvv(pp.pformat(response['InstanceTypeOfferings']))

        # Start with all AZs
        result = set(self.get_azs(region))

        # Get the intersection of all AZs
        for instance_type in instance_types:
            instance_type_azs = set()
            for offering in response['InstanceTypeOfferings']:
                if offering['InstanceType'] == instance_type:
                    instance_type_azs.add(offering['Location'])

            # Reduce the set
            result = result & instance_type_azs

        return result

    def describe_reservations(self, region, availability_zone='*'):
        """Filter reservations by tag and return Ids"""

        filters = [{'Name':'state', 'Values':['active','pending']}]
        if availability_zone is not None and availability_zone != '*' and availability_zone != '':
            filters.append({'Name': 'availability-zone', 'Values': [availability_zone]})

        response = self.clients[region].describe_capacity_reservations(
            Filters=filters,
        )

        check_response(response)

        display.vvvvv(pp.pformat(response))
        result = list(
            filter(lambda elem: tag_match(self.tags, elem['Tags']),
                   response['CapacityReservations']))

        return [i['CapacityReservationId'] for i in result]

    def cancel_reservation(self, region, reservation_id):
        """Cancel a reservation by ID"""

        response = self.clients[region].cancel_capacity_reservation(
            CapacityReservationId=reservation_id,
        )
        display.vvvv(pp.pformat(response))

        check_response(response)

        display.display("Reservation canceled: %s  (%s)" %(reservation_id, region))

    def cancel_all_reservations(self, region):
        """Cancel all reservations in a region matching tags.

        Return the number of canceled reservations."""
        reservation_ids = self.describe_reservations(region)
        for r_id in reservation_ids:
            self.cancel_reservation(region, r_id)
        return len(reservation_ids)

    def create_reservation(self, region, availability_zone, reservation):
        """Create a reservation in an Availability Zone.

        On success:
            Return True, reservation_id
        On Failure:
            Return False, ''
        """
        try:
            reservation_translated = {
                translate_to_api_names(k): v for k, v in reservation.items()
            }

            try:
                duration = parse_duration(self.ttl)
            except Exception as err:
                six.raise_from(AnsibleError("could not parse duration {}".format(self.ttl)), err)

            if len(self.tags) > 0:
                tag_spec =[{
                    'ResourceType': 'capacity-reservation',
                    'Tags':self.tags,
                }]
            else:
                tag_spec = []

            response = self.clients[region].create_capacity_reservation(
                AvailabilityZone=availability_zone,
                EndDate=datetime.datetime.now() + duration,
                EndDateType='limited',
                InstanceMatchCriteria='open',
                TagSpecifications=tag_spec,
                **reservation_translated
            )

            check_response(response)
            display.vvvv("response: %s" % pp.pformat(response))

            display.vvv(pp.pformat(response))
        except botocore.exceptions.ClientError as err:
            if 'InstanceLimitExceeded' in str(err):
                display.display("InstanceLimitExceeded %s - %d * %s"
                                %(availability_zone,
                                  reservation['instance_count'],
                                  reservation['instance_type']))
                return False, ''

            if 'InsufficientInstanceCapacity' in str(err):
                display.display("InsufficientInstanceCapacity %s - %d * %s"
                                %(availability_zone, reservation['instance_count'],
                                    reservation['instance_type']))

                return False, ''

            display.error(pp.pformat(err))
            six.raise_from(AnsibleError("Client Error while creating reservation."), err)

        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            # if success, continue
            r_id = response['CapacityReservation']['CapacityReservationId']
            display.display("Reservation created: %s (%s)" %(r_id, availability_zone))
            return True, r_id

        return False, ''


    def create_reservations(self, region, availability_zone, reservations):
        """Create all reservations in the specified AZ

        Return a tuple (ok, reservations_ids)

        On success:
            ok is True
            reservations_ids is the list of capacity-reservation IDs created

        On failure:
            ok is False
            reservation_ids is the empty list
        """
        reservation_ids = []
        for reservation in reservations:
            if self.dry_run:
                continue

            # sanitize
            reservation['instance_count'] = int(reservation['instance_count'])

            return_ok, reservation_id = self.create_reservation(
                region,
                availability_zone,
                reservation)

            if not return_ok:
                display.display(
                    "Reservation could not be created in %s, trying next AZ."
                    %(availability_zone)
                )
                for r_id in reservation_ids:
                    self.cancel_reservation(region, r_id)

                return False, []

            reservation_ids.append(reservation_id)

        return True, reservation_ids

    def do_reservation_group(self, region, reservation_group, az_done):
        """Determine the AZs with matching instance-type offerings.

        Try to create capacity reservations in one of those AZs.
        If fails, move the next matching AZ.
        If all fail, fail.

        On success:
        Return True, availability_zone, reservation_ids

        On failure:
        Return False, '', empty list
        """
        display.v("..loop2: reservation_group: %s" % (pp.pformat(reservation_group)))

        all_instance_types = set(
            i['instance_type'] for i in reservation_group
        )
        matching_azs = self.filter_azs(region, all_instance_types)
        if self.distinct:
            matching_azs = matching_azs - az_done

        display.v(
            "..loop2: AZs with matching offerings for group: %s" %
            (pp.pformat(matching_azs)))

        for availability_zone in matching_azs:
            display.v("...loop3: trying AZ %s" %(availability_zone))

            r_ok, reservation_ids = self.create_reservations(
                region,
                availability_zone,
                reservation_group)

            if r_ok:
                return True, availability_zone, reservation_ids

        return False, '', []

    def do_region(self, region, reservation_groups):
        """Create reservations, try a region.

        On success:
            Return True,
                   {
                     'az1': {
                         'availability_zone': ...,
                         'reservation_ids': ...,
                     },
                     ...
                   }

        On failure:
            Return False, {}
        """


        display.v(".loop1: Trying region %s" % (region))

        if region not in self.clients:
            self.set_client(region)

        display.v(".loop1: available AZs: %s" % self.get_azs(region))

        result = {}
        az_done = set()
        for reservation_group_name in sorted(reservation_groups):
            reservation_group = reservation_groups[reservation_group_name]
            display.v("..loop2: group %s" %(reservation_group_name))
            r_ok, availability_zone, reservation_ids = self.do_reservation_group(
                region,
                reservation_group,
                az_done,
            )

            if not r_ok:
                # cancel all reservations made in that region
                self.cancel_all_reservations(region)
                return False, {}

            result[reservation_group_name] = {
                'availability_zone': availability_zone,
                'reservation_ids': reservation_ids,
            }
            az_done.add(availability_zone)

        return True, result

    def set_client(self, region):
        """Create and save boto3 EC2 client for a region"""
        self.clients[region] = boto3.client('ec2',
                                            aws_access_key_id=self.aws_key,
                                            aws_secret_access_key=self.aws_secret,
                                            region_name=region,
                                            )

    def __init__(self, aws_key, aws_secret, task_vars, ttl, dry_run=False, distinct=False):
        self.aws_key = aws_key
        self.aws_secret = aws_secret
        self.distinct = distinct
        self.tags = []
        self.ttl = ttl
        self.clients = {}
        self.availability_zones = {}
        if 'odcr_DRYRUN' in task_vars:
            self.dry_run = True
        else:
            self.dry_run = False

        if 'uuid' in task_vars:
            self.tags.append({'Key': 'uuid', 'Value': task_vars['uuid']})

        self.tags.append({'Key': 'guid', 'Value': task_vars['guid']})
        self.tags.append({'Key': 'created-by', 'Value': 'agnosticd'})

class ActionModule(ActionBase):
    """ActionModule Class"""
    _VALID_ARGS = frozenset((
        'reservations',
        'regions',
        'aws_access_key_id',
        'aws_secret_access_key',
        'ttl',
        'state'
    ))
    def run(self, tmp=None, task_vars=None):
        self._supports_check_mode = True

        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)
        del tmp # tmp no longer has any effect

        ttl = self._task.args.get('ttl', '1h')
        distinct = self._task.args.get('distinct', False)
        if isinstance(distinct, six.string_types):
            if distinct.lower() in ['true', 'y', 'yes']:
                distinct = True
            if distinct.lower() in ['false', 'n', 'no']:
                distinct = False

        if not isinstance(distinct, bool):
            result['failed'] = True
            result['error'] = 'distinct must be a boolean'
            return result

        state = self._task.args.get('state', 'present')

        aws_access_key_id = self._task.args.get('aws_access_key_id')
        aws_secret_access_key = self._task.args.get('aws_secret_access_key')
        if not aws_access_key_id or not aws_secret_access_key:
            result['failed'] = True
            result['error'] = 'aws_access_key_id and aws_secret_access_key arg must be passed'
            return result

        reservations = self._task.args.get('reservations', {})

        regions = self._task.args.get('regions', [])


        odcr = ODCRFactory(
            aws_key = aws_access_key_id,
            aws_secret = aws_secret_access_key,
            task_vars = task_vars,
            ttl=ttl,
            distinct=distinct,
        )

        try:
            # First, cleanup all reservations matching tags
            total_canceled = 0
            for region in set(regions):
                odcr.set_client(region)
                total_canceled += odcr.cancel_all_reservations(region)
            if total_canceled > 0:
                result['changed'] = True
        except Exception as err:
            result['failed'] = True
            result['error'] = str(err)
            return result

        if state == 'absent':
            return result

        display.v("# input\n%s" % pp.pformat(reservations))
        display.v("regions: %s" % regions)
        display.v("ttl: %s" % ttl)

        for region in regions:
            try:
                r_ok, result['reservations'] = odcr.do_region(region, reservations)
            except Exception as err:
                result['failed'] = True
                result['error'] = str(err)
                break
            if r_ok:
                # In case of a single availability zone
                if len(result['reservations']) == 1:
                    for k in list(result['reservations']):
                        result['single_availability_zone'] = result['reservations'][k]['availability_zone']

                result['region'] = region
                break

            # All reservation groups could not be created in the available AZs
            display.display(
                "Reservations could not be created in %s, trying next region."
                %(region)
            )
        else:
            display.display("No more regions.")
            result['failed'] = True
            result['error'] = "Reservations could not be created."

        return result
