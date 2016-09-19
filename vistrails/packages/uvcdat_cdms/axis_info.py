import cdtime


def axis_values(axis):
    formatter = format_axis(axis)
    values = []
    for value in axis:
        values.append(formatter(value))
    return values


def selector_value(index, axis):
    if axis.isTime():
        return format_time_axis(axis)(index)
    return axis[index]


def format_axis(axis):
    """Returns a function that converts values from this axis into human readable values"""
    if axis.isTime():
        return format_time_axis(axis)
    elif axis.isLatitude() or axis.isLongitude():
        return format_degrees(axis)
    else:
        return lambda i: unicode(axis[i]) + axis.units


def parse_axis(axis):
    """Returns a function that converts human readable values from this axis to axis values"""
    if axis.isTime():
        return parse_time_axis(axis)
    elif axis.isLatitude() or axis.isLongitude():
        return parse_degrees
    return float


def parse_degrees(value):
    f = value[:-1]
    return float(f)


def format_degrees(axis):
    def format(index):
        return u"%.02f\N{DEGREE SIGN}" % axis[index]
    return format


def format_time_axis(axis):
    """Create a function to prettify a time axis value"""
    units = axis.units
    time_increment = units.split(" ")[0]
    calendar = axis.getCalendar()

    def format(value):
        reltime = cdtime.reltime(axis[value], units)
        comptime = reltime.tocomp(calendar)
        if time_increment[0:6] == "second":
            return "%d-%02d-%02d %02d:%02d:%02d" % (comptime.year, comptime.month, comptime.day, comptime.hour, comptime.minute, comptime.second)
        elif time_increment[0:6] == "minute":
            return "%d-%02d-%02d %02d:%02d" % (comptime.year, comptime.month, comptime.day, comptime.hour, comptime.minute)
        elif time_increment[0:4] == "hour":
            return "%d-%02d-%02d %02d:00" % (comptime.year, comptime.month, comptime.day, comptime.hour)
        elif time_increment[0:3] == "day" or time_increment[0:4] == "week":
            return "%d-%02d-%02d" % (comptime.year, comptime.month, comptime.day)
        elif time_increment[0:5] == "month" or time_increment[0:6] == "season":
            return "%d-%02d" % (comptime.year, comptime.month)
        elif time_increment[0:4] == "year":
            return comptime.year

    return format


def parse_time_axis(axis):
    """Create a function to retrieve indices from string"""
    units = axis.units
    time_increment = units.split(" ")[0]
    calendar = axis.getCalendar()

    def parse(value):
        parts = value.split(" ")
        if len(parts) == 1:
            # It's just a date
            date = value
            time = "0:0:0"
        else:
            date, time = parts

        # Parse date
        date_parts = date.split("-")
        num_date = [int(d) for d in date_parts if d != '']
        num_date += [0 for _ in range(3 - len(num_date))]
        year, month, day = num_date

        time_parts = time.split(":")
        num_time = [int(t) for t in time_parts if t != '']
        num_time += [0 for _ in range(3 - len(num_time))]
        hour, minute, second = num_time

        # Check if the units match up with the specificity
        if time_increment[0:6] == "second":
            if 0 in (year, month, day, hour, minute, second):
                return None
        elif time_increment[0:6] == "minute":
            if 0 in (year, month, day, hour, minute):
                return None
        elif time_increment[0:4] == "hour":
            if 0 in (year, month, day, hour):
                return None
        elif time_increment[0:3] == "day" or time_increment[0:4] == "week":
            if 0 in (year, month, day):
                return None
        elif time_increment[0:5] == "month" or time_increment[0:6] == "season":
            if 0 in (year, month):
                return None
        elif time_increment[0:4] == "year":
            if 0 in (year):
                return None

        try:
            comptime = cdtime.comptime(year, month, day, hour, minute, second)
            reltime = comptime.torel(units, calendar)
            return reltime.value
        except:
            return None
    return parse
