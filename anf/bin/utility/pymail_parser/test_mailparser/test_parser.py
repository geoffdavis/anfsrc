#!/usr/bin/env python
"""Describe file"""
import re
from collections import OrderedDict

import pytest
import email

from mailparser.parser import get_first_part, bounds, LON_BOUNDS, LAT_BOUNDS, Coords, Date, StationCode
from mailparser.parser import fmtyday
from mailparser.parser import process


EMAILFILES = ['test_mailparser/data/test_emails/1']


@pytest.fixture(params=EMAILFILES)
def message(request):
    with open(request.param, 'rb') as fp:
        yield email.message_from_file(fp)


def test_get_first_part(message):
    assert get_first_part(message)


@pytest.mark.parametrize('boundrange, bounds', [
    (bounds.lat, LAT_BOUNDS),
    (bounds.lon, LON_BOUNDS),
])
def test_boundschecker(boundrange, bounds):
    (lower, upper) = bounds
    assert lower in boundrange
    assert lower - 1 not in boundrange
    assert upper not in boundrange
    assert upper - 1 in boundrange


from datetime import datetime


def test_date_format():
    d = datetime(1999, 1, 1)
    s = fmtyday(d)
    assert s == "1999001"


# split email into lines
# for each line:
#   run patterns to extract fields
#       return dict of strings

# convert types of strings

# assign to object (validate in properties)


def test_process(mocker):
    r = process(['hello world', 'gps: 1,-60', 'date: 01/01/1999'])
    assert r == OrderedDict([(Coords, (-60, 1)), (Date, datetime(1999, 1, 1))])


@pytest.mark.parametrize('case', [
    ('date: 01/01/1999', ('1999', '01', '01')),
    ('date: 01-01-1999', ('1999', '01', '01')),
    ('date: 01 01 1999', ('1999', '01', '01')),
    ('Date: 05/26-5/27/16 UTC', ('16', '5', '27')),
    ('Date: 05/28/16-5/29/16 UTC', ('16', '5', '29')),
    ('Date: 05/28/16-05/29/16 UTC', ('16', '05', '29')),
    ('Date: 5/28/16-05/29/16 UTC', ('16', '05', '29')),
])
def test_date_pattern(case):
    line, expected = case
    m = Date.pattern.match(line)
    assert m.group('year', 'month', 'day') == expected


@pytest.mark.parametrize('case', [
    ('GPS: 58.6097367, 152.3941867', ('152.3941867', '58.6097367')),
    ('GPS: 58.6097367, -152.3941867', ('-152.3941867', '58.6097367')),
    ('GPS: -58.6097367, -152.3941867', ('-152.3941867', '-58.6097367')),
    ('GPS: -58.6097367, 152.3941867', ('152.3941867', '-58.6097367')),
    ('gps: 58, 152', ('152', '58')),
    ('gps: 58, -152', ('-152', '58')),
    ('gps: -58, 152', ('152', '-58')),
    ('gps: -58, -152', ('-152', '-58')),
    ('gps: -58, 152', ('152', '-58')),
])
def test_coords_pattern(case):
    line, expected = case
    m = Coords.pattern.match(line)
    assert m.group('lon', 'lat') == expected


@pytest.mark.parametrize('case', [
    ('Station Code: TA.T35M', 'T35M'),
    ('Station Code: TA. P16K', 'P16K'),
    ('Station Code: TA.AK.COLD', 'COLD'),
    ('Station Code: AK.CAST', 'CAST'),
    ('Station Code: TA.PPD', 'PPD'),
    ('Station Code: AK.KAI', 'KAI'),
    # TODO not sure how to handle these yet
    # ('Station Code:=C2=A0 L02F=20', 'L02F'),
    # ('Station Code:&nbsp; L02F <br id=3D"yui_3_16_0_ym19_1_1462280670632_16752">', 'L02F'),
])
def test_sta_pattern(case):
    line, expected = case
    m = StationCode.pattern.match(line)
    assert m.group('sfx') == expected

