#!/usr/bin/python2.7

# requires Python 2.x - not tested with Python 3.x

import serial
import requests

from config import *

DEFAULT_HEADER = '#h,-,18,W,V,A,WH,Cost,WH/Mo,Cost/Mo,Wmax,Vmax,Amax,Wmin,Vmin,Amin,PF,DC,PC,Hz,VA;'

UNIT_MULTIPLIERS = {
    # <W> Integer, watts * 10. (Tenths of watts); 0 - 50000 [2 bytes].
    # <V> Integer, volts * 10. (Tenths of volts); 900 - 2800 [2 bytes].
    # <A> Integer, amps * 10. (Thousandths of amps); 0 - 20000 [2 bytes].
    # <WH> Integer, watt-hours * 10. (Tenths of watt-hours); 0 - 2398800000 (= 5000W * 24
    # hr/day * 1999 days * 10 tenths/unit) [4 bytes].
    # <Cost> Integer, mils. (Tenths of cents or other currency); 0 - 4294967296 (= 2^32-1;
    # 5kW * 65500 mils/kW-hr * 24 hr/day * 546 days, or 5kW * 17900 mils/kW-hr * 24 hr/day
    # * 1999 days, or 1366W * 65500 mils/kW-hr * 24 hr/day * 1999 days) [4 bytes].
    # <WH/Mo> Integer, Watt Hours (Units of WHrs); 0 - 3600000 (= 5000W * 24 hr/day * 30
    # day/mo) [3 bytes].
    # <Cost/Mo> Integer, mils (Tenths of cents or other currency); 0 - 235800000 (= 5kW *
    # 65500 mils/kW-hr * 24 hr/day * 30 days) [4 bytes].
    # <PF> Power factor, percent ratio of Watts versus Volt Amps; 0 - 100 [1 byte].
    # <DC> Duty cycle, percent of the time on versus total time; 0 - 100 [1 byte].
    # <PC> Power Cycle: Integer, number of power-on events indicates that power was
    # removed at some point during this sampling interval since last memory clear; 0 - 255
    # [1 byte].
    # <HZ> Line Frequency, hertz * 10 (tenths of hertz), 400 - 700 [2 bytes].
    # <VA> Volt-Amps, VA * 10 (tenths of volt-amps); 0 - 50000 [2 bytes].
    'W': .1,
    'V': .1,
    'A': .001,
    'WH': .1,
    'Cost': .001,
    'WH/Mo': .1,
    'Cost/Mo': .001,
    'PF': .01,
    'DC': .01,
    'PC': 1,
    'HZ': .1,
    'VA': .1,
}


def get_packet(s):
    ret = ''
    next_char = s.read()
    while next_char != ';':
        if next_char == '#':
            # ret = '#'
            ret = ''
        else:
            ret += next_char
        next_char = s.read()

    # ret += ';'

    return ret


def fake_flush(s):
    old_timeout = s.timeout
    s.timeout = .2
    s.read(5000)
    s.timeout = old_timeout


def process_logging_packet(p, header=DEFAULT_HEADER):
    column_headings = header.split(',')
    columns = p.split(',')

    ret = {}

    for i in range(3, len(columns)):
        field = column_headings[i]
        if columns[i].isdigit():
            columns[i] = int(columns[i])
        if field in UNIT_MULTIPLIERS:
            columns[i] *= UNIT_MULTIPLIERS[field]
        ret[field] = columns[i]

    return ret


def post_watt_hours(d):
    r = requests.post(
        url=POST_URL,
        auth=(POST_USERNAME, POST_PASSWORD),
        data={'watt_hours': int(d)},
        timeout=5,
    )

    print(r)


def main():
    s = serial.Serial(SERIAL_PATH, baudrate=115200, timeout=3)

    count = 0

    try:

        # H,R,0;
        # h,-,18,W,V,A,WH,Cost,WH/Mo,Cost/Mo,Wmax,Vmax,Amax,Wmin,Vmin,Amin,PF,DC,PC,Hz,VA;
        #     Command: Header record request.
        #     Reply: Header record with the shown text.

        fake_flush(s)

        # s.write('#H,R,0;')
        # time.sleep(.1)

        # data = get_packet(s)
        # print("header:" + data)

        # L,W,3,E,<Reserved>,<Interval>;
        # d,...
        #     Command: Set the WattsUp to external Logging with this interval.
        #     Reply: logging output records
        s.write('#L,W,3,E,,1;',)

        fake_flush(s)

        while True:
            p = get_packet(s)
            data = process_logging_packet(p)
            print(data)
            watt_hours = data['WH']
            if count % UPDATE_INTERVAL == 0:
                try:
                    print("POSTING %.1f WH..." % watt_hours)
                    post_watt_hours(watt_hours)
                except Exception as e:
                    print(e)
            count += 1

    except Exception as e:
        print(e)
    finally:
        s.close()


if __name__ == '__main__':
    main()
