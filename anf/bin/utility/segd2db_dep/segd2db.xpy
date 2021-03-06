#
# @authors:
# Juan Reyes <reyes@ucsd.edu>
# Malcolm White <mcwhite@ucsd.edu>
#

import sys
import os
import shutil
import subprocess
from struct import unpack
from collections import OrderedDict
sys.path.append('%s/data/python' % os.environ['ANTELOPE'])
from antelope.datascope import trdestroying,\
                               trnew,\
                               closing,\
                               dbopen,\
                               dbcreate,\
                               DbcreateError
from antelope.stock import str2epoch,\
                           epoch2str
#from segd2db_cython import divide_through

LEAST_SIGNIFICANT_COUNT = 0.000006402437066

class SegDException(Exception):
    """
    New exception for the SEGD class.
    Just empty for now.
    """
    pass

class SegD:
    schema = OrderedDict([('General Header',
                OrderedDict([('General Header Block #1',
                    OrderedDict([('block_length_in_bytes', 32),
                                 ('file_number',
                                        {'start': 1,
                                         'nibbles': 4,
                                         'type': 'bcd',
                                         'description': 'File number (0-9999)',
                                         'notes': 'Set to FFFF when the file '\
                                            'number is greater than 9999. The '\
                                            'expanded file number is contained'\
                                            ' in bytes 1-3 of General Header '\
                                            'Block #2.'
                                        }
                                 ),
                                 ('data_sample_format_code',
                                        {'start': 3,
                                        'nibbles': 4,
                                        'type': 'bcd',
                                        'description': 'Data sample format '\
                                            'code (8058)',
                                        'notes': ''
                                        }
                                 ),
                                 ('general_constants',
                                        {'start': 5,
                                         'nibbles': 12,
                                         'type': 'bcd',
                                         'description': 'General constants',
                                         'notes': ''
                                        }
                                 ),
                                 ('first_shot_last_two_digits_of_year',
                                        {'start': 11,
                                         'nibbles': 2,
                                         'type': 'bcd',
                                         'description': 'First shot point or '\
                                            'time slice last two digits of '\
                                            'year',
                                         'notes': ''
                                        }
                                 ),
                                 ('number_of_additional_general_header_blocks',
                                        {'start': 12,
                                         'nibbles': 1,
                                         'type': 'binary',
                                         'description': 'Number of additional '\
                                            'general header blocks (1)',
                                         'notes': ''
                                        }
                                 ),
                                 ('first_shot_julian_day',
                                        {'start': 12.5,
                                         'nibbles': 3,
                                         'type': 'bcd',
                                         'description': 'First shot point or '\
                                            'time slice Julian day in year',
                                         'notes': ''
                                        }
                                 ),
                                 ('first_shot_UTC_time',
                                        {'start': 14,
                                         'nibbles': 6,
                                         'type': 'bcd',
                                         'description': 'First shot point or '\
                                            'time slice UTC time (HHMMSS)',
                                         'notes': ''
                                        }
                                 ),
                                 ('manufacturers_code',
                                        {'start': 17,
                                         'nibbles': 2,
                                         'type': 'bcd',
                                         'description': 'Manufacturer\'s code '\
                                            '(20)',
                                         'notes': ''
                                        }
                                  ),
                                  ('manufacturers_serial_number',
                                        {'start': 18,
                                         'nibbles': 4,
                                         'type': 'bcd',
                                         'description': 'Manufacturer\'s '\
                                            'serial number',
                                         'notes': ''
                                        }
                                 ),
                                 ('not_used_1',
                                        {'start': 20,
                                         'nibbles': 6,
                                         'type': 'bcd',
                                         'description': 'Not used (0)',
                                         'notes': ''
                                        }
                                 ),
                                 ('base_scan_interval',
                                        {'start': 23,
                                         'nibbles': 2,
                                         'type': 'binary',
                                         'description': 'Base scan interval',
                                         'notes': ''
                                        }
                                 ),
                                 ('polarity_code',
                                        {'start': 24,
                                         'nibbles': 1,
                                         'type': 'binary',
                                         'description': 'Polarity code (0)',
                                         'notes': ''
                                        }
                                 ),
                                 ('not_used_2',
                                        {'start': 24.5,
                                         'nibbles': 3,
                                         'type': 'binary',
                                         'description': 'Not used (0)',
                                         'notes': ''
                                        }
                                 ),
                                 ('record_type',
                                        {'start': 26,
                                         'nibbles': 1,
                                         'type': 'binary',
                                         'description': 'Record type (0)',
                                         'notes': 'Moved to trace header (set '\
                                            'to 0)'
                                        }
                                 ),
                                 ('record_length_in_increments_of_512_1000ths_'\
                                    'of_a_second',
                                        {'start': 26.5,
                                         'nibbles': 3,
                                         'type': 'bcd',
                                         'description': 'Record length in '\
                                            'increments of 0.512 seconds (FFF)',
                                         'notes': 'Use value stored in '\
                                            'General Header Block #2 - bytes '\
                                            '15-17.'
                                        }
                                 ),
                                 ('scan_types_per_record',
                                        {'start': 28,
                                         'nibbles': 2,
                                         'type': 'bcd',
                                         'description': 'Scan types per '\
                                            'record (01)',
                                         'notes': ''
                                        }
                                 ),
                                 ('channel_sets_per_scan_type',
                                        {'start': 29,
                                         'nibbles': 2,
                                         'type': 'bcd',
                                         'description': 'Channel sets per '\
                                            'scan type',
                                         'notes': ''
                                        }
                                 ),
                                 ('number_of_32_byte_skew_blocks',
                                            {'start': 30,
                                             'nibbles': 2,
                                             'type': 'bcd',
                                             'description': 'Number of '\
                                                '32-byte skew blocks (0)',
                                             'notes': ''
                                            }
                                 ),
                                 ('number_of_32_byte_extended_header_blocks',
                                            {'start': 31,
                                             'nibbles': 2,
                                             'type': 'bcd',
                                             'description': 'Number of '\
                                                '32-byte Extended Header '\
                                                'Blocks (00-99 or FF... use '\
                                                'value in General Header '\
                                                'Block #2)',
                                             'notes': ''
                                            }
                                 ),
                                 ('number_of_32_byte_external_header_blocks',
                                            {'start': 32,
                                             'nibbles': 2,
                                             'type': 'bcd',
                                             'description': 'Number of of '\
                                                '32-byte External Header '\
                                                'Blocks (00-99 or FF... use '\
                                                'value in General Header '\
                                                'Block #2)',
                                             'notes': ''
                                            }
                                 )
                                ])
                            ),
                ('General Header Block #2',
                    OrderedDict([('block_length_in_bytes', 32),
                                 ('extended_file_number',
                                        {'start': 1,
                                         'nibbles': 6,
                                         'type': 'binary',
                                         'description': 'Extended file number',
                                         'notes': ''
                                        }
                                 ),
                                 ('extended_channel_sets_per_scan_type',
                                        {'start': 2,
                                         'nibbles': 4,
                                         'type': 'binary',
                                         'description': 'Extended channel '\
                                            'sets per scan type',
                                         'notes': ''
                                        }
                                 ),
                                 ('extended_header_blocks',
                                        {'start': 6,
                                         'nibbles': 4,
                                         'type': 'binary',
                                         'description': 'Extended header '\
                                            'blocks',
                                         'notes': ''
                                        }
                                 ),
                                 ('external_header_blocks',
                                        {'start': 8,
                                         'nibbles': 6,
                                         'type': 'binary',
                                         'description': 'External header '\
                                            'blocks',
                                         'notes': 'Now 3 bytes instead of 2.'
                                        }
                                 ),
                                 ('fairfield_file_version_number',
                                        {'start': 11,
                                         'nibbles': 4,
                                         'type': 'binary',
                                         'description': 'Fairfield file '\
                                            'version number',
                                         'notes': 'One byte unsigned binary '\
                                            'and one byte binary fraction. '\
                                            'This version: 0x0105'
                                        }
                                 ),
                                 ('number_of_32_byte_general_trailer_blocks',
                                        {'start': 13,
                                         'nibbles': 4,
                                         'type': 'binary',
                                         'description': 'Number of 32-byte '\
                                            'general trailer blocks (0)',
                                         'notes': ''
                                        }
                                 ),
                                 ('extended_record_length_in_milliseconds',
                                        {'start': 15,
                                         'nibbles': 6,
                                         'type': 'binary',
                                         'description': 'Extended record '\
                                            'length in milliseconds',
                                         'notes': ''
                                        }
                                 ),
                                 ('undefined_1',
                                        {'start': 18,
                                         'nibbles': 2,
                                         'type': 'binary',
                                         'description': 'Undefined (0)',
                                         'notes': ''
                                        }
                                 ),
                                 ('general_header_block_number',
                                        {'start': 19,
                                         'nibbles': 2,
                                         'type': 'binary',
                                         'description': 'General header '\
                                            'block number (2)',
                                         'notes': ''
                                        }
                                 ),
                                 ('undefined_2',
                                        {'start': 20,
                                         'nibbles': 26,
                                         'type': 'binary',
                                         'description': 'Undefined (0)',
                                         'notes': ''
                                        }
                                 )])
                        )])
                ),
                ('Channel Set Descriptor',
                    OrderedDict([('Main Block',
                        OrderedDict([('block_length_in_bytes', 32),
                                 ('scan_type_number',
                                        {'start': 1,
                                         'nibbles': 2,
                                         'type': 'bcd',
                                         'description': 'Scan type number (1)',
                                         'notes': ''
                                         }
                                 ),
                                 ('channel_set_number',
                                        {'start': 2,
                                         'nibbles': 2,
                                         'type': 'bcd',
                                         'description': 'Channel set number',
                                         'notes': ''
                                         }
                                 ),
                                 ('channel_set_start_time_in_milliseconds_by_2',
                                        {'start': 3,
                                         'nibbles': 4,
                                         'type': 'binary',
                                         'description': 'Channel set start '\
                                            'time in milliseconds / 2',
                                         'notes': ''
                                         }
                                 ),
                                 ('channel_set_end_time_in_milliseconds_by_2',
                                        {'start': 5,
                                         'nibbles': 4,
                                         'type': 'binary',
                                         'description': 'Channel set end time '\
                                            'in milliseconds / 2',
                                         'notes': ''
                                         }
                                 ),
                                 ('optional_mp_factor_extension_byte',
                                        {'start': 7,
                                         'nibbles': 2,
                                         'type': 'binary',
                                         'description': 'Optional MP factor '\
                                            'extension byte (0)',
                                         'notes': ''
                                         }
                                 ),
                                 ('mp_factor_descaler_multiplier',
                                        {'start': 8,
                                         'nibbles': 2,
                                         'type': 'binary',
                                         'description': 'MP factor descaler '\
                                            'multiplier (0)',
                                         'notes': 'Fairfield data is already '\
                                            'descaled to millivolts.'
                                         }
                                 ),
                                 ('number_of_channels_in_channel_set',
                                        {'start': 9,
                                         'nibbles': 4,
                                         'type': 'bcd',
                                         'description': 'Number of channels '\
                                            'in channel set',
                                         'notes': ''
                                         }
                                 ),
                                 ('channel_type_code',
                                        {'start': 11,
                                         'nibbles': 1,
                                         'type': 'binary',
                                         'description': 'Channel type code (1)',
                                         'notes': 'High order 4-bits'
                                         }
                                 ),
                                 ('undefined_3',
                                        {'start': 11.5,
                                         'nibbles': 1,
                                         'type': 'binary',
                                         'description': 'Unused',
                                         'notes': ''
                                         }
                                 ),
                                 ('number_of_subscans',
                                        {'start': 12,
                                         'nibbles': 1,
                                         'type': 'bcd',
                                         'description': 'Number of sub-scans',
                                         'notes': 'High order 4-bits'
                                         }
                                 ),
                                 ('gain_control_type',
                                        {'start': 12.5,
                                         'nibbles': 1,
                                         'type': 'bcd',
                                         'description': 'Gain control type (3)',
                                         'notes': 'Low order 4-bits)'
                                         }
                                 ),
                                 ('alias_filter_frequency_in_Hz',
                                        {'start': 13,
                                         'nibbles': 4,
                                         'type': 'bcd',
                                         'description': 'Alias filter '\
                                            'frequency in Hertz',
                                         'notes': ''
                                         }
                                 ),
                                 ('alias_filter_slope_in_dB_per_octave',
                                        {'start': 15,
                                         'nibbles': 4,
                                         'type': 'bcd',
                                         'description': 'Alias filter slope '\
                                            'in dB per octave',
                                         'notes': ''
                                         }
                                 ),
                                 ('low_cut_filter_frequency_in_Hz',
                                        {'start': 17,
                                         'nibbles': 4,
                                         'type': 'bcd',
                                         'description': 'Low cut filter '\
                                            'frequency in Hertz',
                                         'notes': ''
                                         }
                                 ),
                                 ('low_cut_filter_slope_in_dB_per_octave',
                                        {'start': 19,
                                         'nibbles': 4,
                                         'type': 'bcd',
                                         'description': 'Low cut filter slope '\
                                            'in dB per octave',
                                         'notes': ''
                                         }
                                 ),
                                 ('notch_filter_frequency_in_Hz_x_10',
                                        {'start': 21,
                                         'nibbles': 4,
                                         'type': 'bcd',
                                         'description': 'Notch filter '\
                                            'frequency in Hertz x 10',
                                         'notes': ''
                                         }
                                 ),
                                 ('second_notch_filter_frequency_in_Hz_x_10',
                                        {'start': 23,
                                         'nibbles': 4,
                                         'type': 'bcd',
                                         'description': 'Second notch filter '\
                                            'frequency in Hertz x 10',
                                         'notes': ''
                                         }
                                 ),
                                 ('third_notch_filter_frequency_in_Hz_x_10',
                                        {'start': 25,
                                         'nibbles': 4,
                                         'type': 'bcd',
                                         'description': 'Third notch filter '\
                                            'frequency in Hertz x 10',
                                         'notes': ''
                                         }
                                 ),
                                 ('exteneded_channel_set_number',
                                        {'start': 27,
                                         'nibbles': 4,
                                         'type': 'binary',
                                         'description': 'Extended channel set '\
                                            'number',
                                         'notes': ''
                                         }
                                 ),
                                 ('extended_header_flag',
                                        {'start': 29,
                                         'nibbles': 1,
                                         'type': 'binary',
                                         'description': 'Extended header flag',
                                         'notes': ''
                                         }
                                 ),
                                 ('number_of_32_byte_trace_header_extensions',
                                        {'start': 29.5,
                                         'nibbles': 1,
                                         'type': 'binary',
                                         'description': 'Number of 32-byte '\
                                            'trace header extensions',
                                         'notes': ''
                                         }
                                 ),
                                 ('vertical_stack_size',
                                        {'start': 30,
                                         'nibbles': 2,
                                         'type': 'binary',
                                         'description': 'Vertical stack size (1)',
                                         'notes': ''
                                         }
                                 ),
                                 ('streamer_cable_number',
                                        {'start': 31,
                                         'nibbles': 2,
                                         'type': 'binary',
                                         'description': 'Streamer cable '\
                                            'number (0)',
                                         'notes': ''
                                         }
                                 ),
                                 ('array_forming',
                                        {'start': 32,
                                         'nibbles': 2,
                                         'type': 'binary',
                                         'description': 'Array forming (0)',
                                         'notes': ''
                                         }
                                 )])
                        )])
                    ),
                ('Extended Header',
                        OrderedDict([('32-byte Extended Header Block #1',
                            OrderedDict([('block_length_in_bytes', 32),
                                 ('id_number_of_remote',
                                        {'start': 1,
                                         'nibbles': 16,
                                         'type': 'binary',
                                         'description': 'ID number of remote '\
                                            'unit',
                                         'notes': ''
                                        }
                                 ),
                                 ('epoch_deployment_time',
                                        {'start': 9,
                                         'nibbles': 16,
                                         'type': 'binary',
                                         'description': 'Epoch deployment time',
                                         'notes': ''
                                        }
                                 ),
                                 ('epoch_pickup_time',
                                        {'start': 17,
                                         'nibbles': 16,
                                         'type': 'binary',
                                         'description': 'Epoch pickup time',
                                         'notes': ''
                                        }
                                 ),
                                 ('remote_unit_epoch_start_time',
                                        {'start': 25,
                                         'nibbles': 16,
                                         'type': 'binary',
                                         'description': 'Remote unit epoch '\
                                            'start time',
                                         'notes': ''
                                        }
                                 )])
                            ),
                        ('32-byte Extended Header Block #2',
                            OrderedDict([('block_length_in_bytes', 32),
                                 ('acquisition_drift_window',
                                        {'start': 1,
                                         'nibbles': 8,
                                         'type': 'ieee',
                                         'description': 'Acquisition drift '\
                                            'window (microseconds)',
                                         'notes': 'Only valid if clock '\
                                            'stopped normally. Set to 0.0 if '\
                                            'it died on its own accord.'
                                        }
                                 ),
                                 ('clock_drift',
                                        {'start': 5,
                                         'nibbles': 16,
                                         'type': 'binary',
                                         'description': 'Clock drift '\
                                            '(nanoseconds for this acquisition)',
                                         'notes': ''
                                        }
                                 ),
                                 ('clock_stop_method',
                                        {'start': 13,
                                         'nibbles': 2,
                                         'type': 'binary',
                                         'description': 'Clock stop method',
                                         'notes': '0 - normal\n1 - storage '\
                                            'full (ran out of memory)\n2 - '\
                                            'power loss (ran out of batter '\
                                            'life)\n3 - reboot (by command)'
                                        }
                                 ),
                                 ('frequency_drift_within_specification_flag',
                                        {'start': 14,
                                         'nibbles': 2,
                                         'type': 'binary',
                                         'description': 'Frequency drift '\
                                            'within specification flag',
                                         'notes': '0 - not within '\
                                            'specification\n1 - within '\
                                            'specification'
                                        }
                                 ),
                                 ('oscillator_type',
                                        {'start': 15,
                                         'nibbles': 2,
                                         'type': 'binary',
                                         'description': 'Oscillator type',
                                         'notes': '0 - control board\n1 - '\
                                            'atomic\n2 - ovenized\n3 - double '\
                                            'ovenized\n4 - disciplined',
                                        }
                                 ),
                                 ('data_collection_method',
                                        {'start': 16,
                                         'nibbles': 2,
                                         'type': 'binary',
                                         'description': 'Data collection method',
                                         'notes': '0 - normal (as driven by '\
                                            'real shots)\n1 - continuous '\
                                            '(fixed time slice of all data '\
                                            'contained in remote unit)\n2 - '\
                                            'shot sliced with guard band'
                                        }
                                 ),
                                 ('number_of_records_in_file',
                                        {'start': 17,
                                         'nibbles': 8,
                                         'type': 'binary',
                                         'description': 'Number of records '\
                                            '(shots or time slices) in this '\
                                            'file',
                                         'notes': ''
                                        }
                                 ),
                                 ('total_number_of_files_to_be_acquired_for_'\
                                    'this_remote_unit',
                                        {'start': 21,
                                         'nibbles': 8,
                                         'type': 'binary',
                                         'description': 'Total number of '\
                                            'files to be acquired for this '\
                                            'remote unit',
                                         'notes': ''
                                        }
                                 ),
                                 ('file_number',
                                        {'start': 25,
                                         'nibbles': 8,
                                         'type': 'binary',
                                         'description': 'File number (out of '\
                                            'total number above)',
                                         'notes': ''
                                        }
                                 ),
                                 ('data_decimation_flag',
                                        {'start': 29,
                                         'nibbles': 2,
                                         'type': 'binary',
                                         'description': 'Data decimation flag',
                                         'notes': '0 - not decimated\n1 - '\
                                            'decimated data'
                                        }
                                 ),
                                 ('original_base_scan_interval',
                                        {'start': 30,
                                         'nibbles': 2,
                                         'type': 'binary',
                                         'description': 'Original base scan '\
                                            'interval (set to 0 if not '\
                                            'decimated)',
                                         'notes': ''
                                        }
                                 ),
                                 ('number_of_decimation_filter_coefficients',
                                        {'start': 31,
                                         'nibbles': 4,
                                         'type': 'binary',
                                         'description': 'Number of decimation '\
                                            'filter coefficients (set to 0 if '\
                                            'not decimated)',
                                         'notes': ''
                                        }
                                 )
                            ])
                        ),
                        ('32-byte Extended Header Block #3',
                            OrderedDict([('block_length_in_bytes', 32),
                                 ('receiver_line_number',
                                     {'start': 1,
                                      'nibbles': 8,
                                      'type': 'binary',
                                      'description': 'Receiver line number',
                                      'notes': 'This is replicated here to '\
                                        'facilitate file naming conventions '\
                                        'when making media copies to block devices'
                                     }
                                 ),
                                 ('receiver_point',
                                     {'start': 5,
                                      'nibbles': 8,
                                      'type': 'binary',
                                      'description': 'Receiver point',
                                      'notes': 'This is replicate here to '\
                                        'facilitate file naming conventions '\
                                        'when making media copies to block '\
                                        'devices'
                                     }
                                 ),
                                 ('receiver_point_index',
                                     {'start': 9,
                                      'nibbles': 2,
                                      'type': 'binary',
                                      'description': 'Receiver point index',
                                      'notes': 'This is replicated here to '\
                                        'facilitate file naming conventions '\
                                        'when making media copies to block '\
                                        'devices'
                                     }
                                 ),
                                 ('first_shot_line_written_to_this_file',
                                     {'start': 10,
                                      'nibbles': 8,
                                      'type': 'binary',
                                      'description': 'First shot line written '\
                                        'to this file (set to 0 for '\
                                        'continuous)',
                                      'notes': ''
                                     }
                                 ),
                                 ('first_shot_point_written_to_this_file',
                                     {'start': 14,
                                      'nibbles': 8,
                                      'type': 'binary',
                                      'description': 'First shot point '\
                                        'written to this file (set to 0 for '\
                                        'continuous)',
                                      'notes': ''
                                     }
                                 ),
                                 ('first_shot_point_index_written_to_this_file',
                                     {'start': 18,
                                      'nibbles': 2,
                                      'type': 'binary',
                                      'description': 'First shot point index '\
                                        'written to this file (set to 0 for '\
                                        'continuous)',
                                      'notes': ''
                                     }
                                 ),
                                 ('last_shot_line_written_to_this_file',
                                     {'start': 19,
                                      'nibbles': 8,
                                      'type': 'binary',
                                      'description': 'Last shot line written '\
                                        'to this file (set to 0 for continuous'\
                                        ')',
                                      'notes': ''
                                     }
                                 ),
                                 ('last_shot_point_written_to_this_file',
                                     {'start': 23,
                                      'nibbles': 8,
                                      'type': 'binary',
                                      'description': 'Last shot point written '\
                                        'to this file (set to 0 for continuous'\
                                        ')',
                                      'notes': ''
                                     }
                                 ),
                                 ('last_shot_point_index_written_to_this_file',
                                     {'start': 27,
                                      'nibbles': 2,
                                      'type': 'binary',
                                      'description': 'Last shot point index '\
                                        'written to the file (set to 0 for '\
                                        'continuous)',
                                      'notes': ''
                                     }
                                 )
                            ])
                        ),
                        ('32-byte Extended Header Auxiliary Block',
                            OrderedDict([('block_length_in_bytes', 32),
                                 ('data_decimation_filter_coefficient_1',
                                     {'start': 1,
                                      'nibbles': 8,
                                      'type': 'ieee',
                                      'description': 'Data decimation filter '\
                                        'coeffecient 1',
                                      'notes': ''
                                     }
                                 ),
                                 ('data_decimation_filter_coefficient_2',
                                     {'start': 5,
                                      'nibbles': 8,
                                      'type': 'ieee',
                                      'description': 'Data decimation filter '\
                                        'coeffecient 2',
                                      'notes': ''
                                     }
                                 ),
                                 ('data_decimation_filter_coefficient_3',
                                     {'start': 9,
                                      'nibbles': 8,
                                      'type': 'ieee',
                                      'description': 'Data decimation filter '\
                                        'coeffecient 3',
                                      'notes': ''
                                     }
                                 ),
                                 ('data_decimation_filter_coefficient_4',
                                     {'start': 13,
                                      'nibbles': 8,
                                      'type': 'ieee',
                                      'description': 'Data decimation filter '\
                                        'coeffecient 4',
                                      'notes': ''
                                     }
                                 ),
                                 ('data_decimation_filter_coefficient_5',
                                     {'start': 17,
                                      'nibbles': 8,
                                      'type': 'ieee',
                                      'description': 'Data decimation filter '\
                                        'coeffecient 5',
                                      'notes': ''
                                     }
                                 ),
                                 ('data_decimation_filter_coefficient_6',
                                     {'start': 21,
                                      'nibbles': 8,
                                      'type': 'ieee',
                                      'description': 'Data decimation filter '\
                                        'coeffecient 6',
                                      'notes': ''
                                     }
                                 ),
                                 ('data_decimation_filter_coefficient_7',
                                     {'start': 25,
                                      'nibbles': 8,
                                      'type': 'ieee',
                                      'description': 'Data decimation filter '\
                                        'coeffecient 7',
                                      'notes': ''
                                     }
                                 ),
                                 ('data_decimation_filter_coefficient_8',
                                     {'start': 29,
                                      'nibbles': 8,
                                      'type': 'ieee',
                                      'description': 'Data decimation filter '\
                                        'coeffecient 8',
                                      'notes': ''
                                     }
                                 )
                                ])
                        )])
                ),
                ('External Header',
                    OrderedDict([('External Header Block #1',
                        OrderedDict([('block_length_in_bytes', 32),
                                 ('size',
                                    {'start': 1,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Size (number of 32-byte '\
                                        'external header blocks that contain '\
                                        'information associated with a single '\
                                        'shot)',
                                     'notes': ' The size of each shot will be '\
                                        'set to the maximum size of any shot '\
                                        'in this record. This implies a fixed '\
                                        'blocking to provide a means to index '\
                                        'quickly into desired area.'
                                    }
                                 ),
                                 ('receiver_line_number',
                                    {'start': 5,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Receiver line number',
                                     'notes': 'This is replicated here to '\
                                        'facilitate file naming conventions '\
                                        'when making media copies to block '\
                                        'devices.'
                                    }
                                 ),
                                 ('receiver_point',
                                    {'start': 9,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Receiver point',
                                     'notes': 'This is replicated here to '\
                                        'facilitate file naming conventions '\
                                        'when making media copies to block '\
                                        'devices.'
                                    }
                                 ),
                                 ('receiver_point_index',
                                    {'start': 13,
                                     'nibbles': 2,
                                     'type': 'binary',
                                     'description': 'Receiver point index',
                                     'notes': 'This is replicated here to '\
                                        'facilitate file naming conventions '\
                                        'when making media copies to block '\
                                        'devices.'
                                    }
                                 )
                            ])
                        ),
                        ('32-byte External Header Auxiliary Block',
                            OrderedDict([('block_length_in_bytes', 32),
                                ('shot_epoch_time',
                                    {'start': 1,
                                     'nibbles': 16,
                                     'type': 'binary',
                                     'description': 'Shot epoch time',
                                     'notes': ''
                                     }
                                ),
                                ('shot_line_number',
                                    {'start': 9,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Shot line number',
                                     'notes': ''
                                     }
                                ),
                                ('shot_point',
                                    {'start': 13,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Shot point',
                                     'notes': ''
                                     }
                                ),
                                ('shot_point_index',
                                    {'start': 17,
                                     'nibbles': 2,
                                     'type': 'binary',
                                     'description': 'Shot point index',
                                     'notes': ''
                                     }
                                ),
                                ('shot_point_final_x_coordinate_x_10',
                                    {'start': 18,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Shot point final '\
                                        'x-coordinate x 10',
                                     'notes': ''
                                     }
                                ),
                                ('shot_point_final_y_coordinate_x_10',
                                    {'start': 22,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Shot point final '\
                                        'y-coordinate x 10',
                                     'notes': ''
                                     }
                                ),
                                ('shot_point_final_depth_in_meters_x_10',
                                    {'start': 26,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Shot point final depth '\
                                        'in meters x 10',
                                     'notes': ''
                                     }
                                ),
                                ('source_of_final_shot_information',
                                    {'start': 30,
                                     'nibbles': 2,
                                     'type': 'binary',
                                     'description': 'Source of final shot '\
                                        'information',
                                     'notes': '0 - undefined\n1 - preplan\n2 '\
                                        '- as shot\n3 - post processed'
                                     }
                                ),
                                ('shot_status_flag',
                                    {'start': 31,
                                     'nibbles': 2,
                                     'type': 'binary',
                                     'description': 'Shot status flag',
                                     'notes': '0 - normal\n1 - bad - operator '\
                                        'specified\n3 - bad - failed T0 QC test'
                                     }
                                )
                                ])
                        )])
                ),
                ('Trace Header',
                    OrderedDict([('20-byte Trace Header Block',
                            OrderedDict([('block_length_in_bytes', 20),
                                ('tape_file_number',
                                    {'start': 1,
                                     'nibbles': 4,
                                     'type': 'bcd',
                                     'description': 'Tape file number',
                                     'notes': 'Two byte, four digit, BCD. '\
                                        'These bytes must be set to FFFF when '\
                                        'the Extended file number (bytes '\
                                        '18-20) is used.'
                                    }
                                ),
                                ('scan_type_and_channel_set_number',
                                    {'start': 3,
                                     'nibbles': 4,
                                     'type': 'bcd',
                                     'description': 'Scan type and channel '\
                                        'set number',
                                     'notes': ''
                                    }
                                ),
                                ('trace_number',
                                    {'start': 5,
                                     'nibbles': 4,
                                     'type': 'bcd',
                                     'description': 'Trace number (1 - 9999)',
                                     'notes': ''
                                    }
                                ),
                                ('first_timing_word',
                                    {'start': 7,
                                     'nibbles': 6,
                                     'type': 'bcd',
                                     'description': 'First timing word',
                                     'notes': ''
                                    }
                                ),
                                ('number_of_32_byte_trace_extension_blocks',
                                    {'start': 10,
                                     'nibbles': 2,
                                     'type': 'binary',
                                     'description': 'Number of 32-byte trace '\
                                        'extension blocks',
                                     'notes': ''
                                    }
                                ),
                                ('segd_sample_skew_value',
                                    {'start': 11,
                                     'nibbles': 2,
                                     'type': 'binary',
                                     'description': 'SEG-D sample skew value '\
                                        '(0)',
                                     'notes': ''
                                    }
                                ),
                                ('trace_edit_code',
                                    {'start': 12,
                                     'nibbles': 2,
                                     'type': 'binary',
                                     'description': 'Trace edit code (0)',
                                     'notes': ''
                                    }
                                ),
                                ('time_break_window',
                                    {'start': 13,
                                     'nibbles': 6,
                                     'type': 'binary',
                                     'description': 'Time break window (0)',
                                     'notes': ''
                                    }
                                ),
                                ('extended_channel_set_number',
                                    {'start': 16,
                                     'nibbles': 4,
                                     'type': 'binary',
                                     'description': 'Extended channel set number (0)',
                                     'notes': ''
                                    }
                                ),
                                ('extended_file_number',
                                    {'start': 18,
                                     'nibbles': 6,
                                     'type': 'binary',
                                     'description': 'Extended file number',
                                     'notes': ''
                                    }
                                )
                                ])
                        ),
                        ('32-byte Trace Header Block #1',
                            OrderedDict([('block_length_in_bytes', 32),
                                ('receiver_line_number',
                                    {'start': 1,
                                     'nibbles': 6,
                                     'type': 'binary',
                                     'description': 'Receiver line number',
                                     'notes': 'Two\'s complement, signed'
                                    }
                                ),
                                ('receiver_point',
                                    {'start': 4,
                                     'nibbles': 6,
                                     'type': 'binary',
                                     'description': 'Receiver point',
                                     'notes': 'Two\'s complement, signed'
                                    }
                                ),
                                ('receiver_point_index',
                                    {'start': 7,
                                     'nibbles': 2,
                                     'type': 'binary',
                                     'description': 'Receiver point index',
                                     'notes': 'Two\'s complement, unsigned'
                                    }
                                ),
                                ('number_of_samples_per_trace',
                                    {'start': 8,
                                     'nibbles': 6,
                                     'type': 'binary',
                                     'description': 'Number of samples per trace',
                                     'notes': ''
                                    }
                                ),
                                ('extended_receiver_line_number',
                                    {'start': 11,
                                     'nibbles': 10,
                                     'type': 'binary',
                                     'description': 'Exteneded receiver line '\
                                        'number',
                                     'notes': ''
                                    }
                                ),
                                ('extended_receiver_point_number',
                                    {'start': 16,
                                     'nibbles': 10,
                                     'type': 'binary',
                                     'description': 'Extended receiver point '\
                                        'number',
                                     'notes': ''
                                    }
                                ),
                                ('sensor_type_on_this_trace',
                                    {'start': 21,
                                     'nibbles': 2,
                                     'type': 'binary',
                                     'description': 'Sensor type on this trace',
                                     'notes': '0 - not defined\n1 - hydrophone'\
                                        '\n2 - vertical geophone\n3 - inline '\
                                        'geophone\n4 - cross-line geophone\n5 '\
                                        '- other horizontal geophone\n6 - '\
                                        'vertical accelerometer\n7 - inline '\
                                        'accelerometer\n8 - cross-line '\
                                        'accelerometer\n9 - other horizontal '\
                                        'accelerometer'
                                    }
                                )
                                ])
                        ),
                        ('32-byte Trace Header Block #2',
                            OrderedDict([('block_length_in_bytes', 32),
                                ('remote_unit_serial_number',
                                    {'start': 1,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Remote unit serial number',
                                     'notes': ''
                                    }
                                ),
                                ('time_slice_index_for_this_remote_unit',
                                    {'start': 5,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Time slice index for '\
                                        'this remote unit',
                                     'notes': ''
                                    }
                                )
                                ])
                        ),
                        ('32-byte Trace Header Block #3',
                            OrderedDict([('block_length_in_bytes', 32),
                                ('shot_or_time_slice_epoch_time',
                                    {'start': 1,
                                     'nibbles': 16,
                                     'type': 'binary',
                                     'description': 'Shot or time slice epoch '\
                                        'time',
                                     'notes': ''
                                    }
                                ),
                                ('shot_skew_time_form_sample_boundary',
                                    {'start': 9,
                                     'nibbles': 16,
                                     'type': 'binary',
                                     'description': 'Shot skew time from '\
                                        'sample boundary (microseconds)',
                                     'notes': ''
                                    }
                                ),
                                ('applied_clock_correction_time_shift',
                                    {'start': 17,
                                     'nibbles': 16,
                                     'type': 'binary',
                                     'description': '+/- applied clock '\
                                        'correction time shift (nanoseconds)',
                                     'notes': ''
                                    }
                                ),
                                ('remaining_clock_correction_time_shift',
                                    {'start': 25,
                                     'nibbles': 16,
                                     'type': 'binary',
                                     'description': '+/- remaining (not '\
                                        'applied) clock correction time shift '\
                                        '(nanoseconds)',
                                     'notes': ''
                                    }
                                )
                                ])
                        ),
                        ('32-byte Trace Header Block #4',
                            OrderedDict([('block_length_in_bytes', 32),
                                ('pre_shot_guard_band',
                                    {'start': 1,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Pre-shot guard band '\
                                        '(milliseconds) (set to 0 for '\
                                        'continuous)',
                                     'notes': ''
                                    }
                                ),
                                ('post_shot_guard_band',
                                    {'start': 5,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Post-shot guard band '\
                                        '(milliseconds) (set to 0 for '\
                                        'continuous)',
                                     'notes': ''
                                    }
                                ),
                                ('preamp_gain_in_dB',
                                    {'start': 9,
                                     'nibbles': 2,
                                     'type': 'binary',
                                     'description': 'Preamp gain in dB',
                                     'notes': ''
                                    }
                                ),
                                ('trace_clipped_flag',
                                    {'start': 9,
                                     'nibbles': 2,
                                     'type': 'binary',
                                     'description': 'Trace clipped flag',
                                     'notes': '0 - not clipped\n1 - digital '\
                                        'clip detected\n2 - analog clip '\
                                        'detected'
                                    }
                                ),
                                ('record_type_code',
                                    {'start': 11,
                                     'nibbles': 2,
                                     'type': 'binary',
                                     'description': 'Record type code',
                                     'notes': '0x8 - normal seismic data '\
                                        'record\n0x2 - test data record'
                                    }
                                ),
                                ('shot_status_flag',
                                    {'start': 12,
                                     'nibbles': 2,
                                     'type': 'binary',
                                     'description': 'Shot status flag (set to '\
                                        '0 for continuous)',
                                     'notes': ''
                                    }
                                ),
                                ('post_processed_first_break_pick_time',
                                    {'start': 25,
                                     'nibbles': 8,
                                     'type': 'ieee',
                                     'description': 'Post processed first '\
                                        'break pick time',
                                     'notes': ''
                                    }
                                ),
                                ('post_processed_rms_noise',
                                    {'start': 29,
                                     'nibbles': 8,
                                     'type': 'ieee',
                                     'description': 'Post processed RMS noise',
                                     'notes': ''
                                    }
                                )
                                ])
                        ),
                        ('32-byte Trace Header Block #5',
                            OrderedDict([('block_length_in_bytes', 32),
                                ('receiver_line_number',
                                    {'start': 1,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Receiver line number',
                                     'notes': ''
                                    }
                                ),
                                ('receiver point',
                                    {'start': 5,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Receiver point',
                                     'notes': ''
                                    }
                                ),
                                ('receiever_point_index',
                                    {'start': 9,
                                     'nibbles': 2,
                                     'type': 'binary',
                                     'description': 'Receiver point index',
                                     'notes': ''
                                    }
                                ),
                                ('receiver_point_pre_plan_x_coordinate_x_10',
                                    {'start': 10,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Receiver point pre-plan '\
                                        'x-coordinate x 10',
                                     'notes': ''
                                    }
                                ),
                                ('receiver_point_pre_plan_y_coordinate_x_10',
                                    {'start': 14,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Receiver point pre=plan '\
                                        'y-coordinate x 10',
                                     'notes': ''
                                    }
                                ),
                                ('receiver_point_final_x_coordinate_x_10',
                                    {'start': 18,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Receiver point final '\
                                        'x-coordinate x 10',
                                     'notes': ''
                                    }
                                ),
                                ('receiver_point_final_y_coordinate_x_10',
                                    {'start': 22,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Receiver point final '\
                                        'y-coordinate x 10',
                                     'notes': ''
                                    }
                                ),
                                ('receiver_point_final_depth_x_10',
                                    {'start': 26,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Receiver point final '\
                                        'depth x 10',
                                     'notes': ''
                                    }
                                ),
                                ('source_of_final_receiver_information',
                                    {'start': 30,
                                     'nibbles': 2,
                                     'type': 'binary',
                                     'description': 'Source of final receiver '\
                                        'information',
                                     'notes': '1 - preplan\n2 - as laid (no '\
                                        'navigation sensor)\n3 - as laid '\
                                        '(HiPAP only)\n4 - as laid (HiPAP and '\
                                        'INS)\n5 - as laid (HiPAP and DVL)\n6 '\
                                        '- as laid (HiPAP, DVL and INS)\n7 - '\
                                        'post-processed (HiPAP only)\n8 - '\
                                        'post-processed (HiPAP and INS)\n9 - '\
                                        'post-processed (HiPAP and DVL)\n10 - '\
                                        'post-processed (HiPAP, DVL and INS)\n'\
                                        '11 - first break analysis'
                                    }
                                )
                                ])
                        ),
                        ('32-byte Trace Header Block #6',
                            OrderedDict([('block_length_in_bytes', 32),
                                ('tilt_matrix_element_0',
                                    {'start': 1,
                                     'nibbles': 8,
                                     'type': 'ieee',
                                     'description': 'Tilt matrix element 0 '\
                                        '(H1X)',
                                     'notes': ''
                                    }
                                ),
                                ('tilt_matrix_element_1',
                                    {'start': 5,
                                     'nibbles': 8,
                                     'type': 'ieee',
                                     'description': 'Tilt matrix element 1 '\
                                        '(H2X)',
                                     'notes': ''
                                    }
                                ),
                                ('tilt_matrix_element_2',
                                    {'start': 9,
                                     'nibbles': 8,
                                     'type': 'ieee',
                                     'description': 'Tilt matrix element 2 '\
                                        '(VX)',
                                     'notes': ''
                                    }
                                ),
                                ('tilt_matrix_element_3',
                                    {'start': 13,
                                     'nibbles': 8,
                                     'type': 'ieee',
                                     'description': 'Tilt matrix element 3 '\
                                        '(H1Y)',
                                     'notes': ''
                                    }
                                ),
                                ('tilt_matrix_element_4',
                                    {'start': 17,
                                     'nibbles': 8,
                                     'type': 'ieee',
                                     'description': 'Tilt matrix element 4 '\
                                        '(H2Y)',
                                     'notes': ''
                                    }
                                ),
                                ('tilt_matrix_element_5',
                                    {'start': 21,
                                     'nibbles': 8,
                                     'type': 'ieee',
                                     'description': 'Tilt matrix element 5 '\
                                        '(VY)',
                                     'notes': ''
                                    }
                                ),
                                ('tilt_matrix_element_6',
                                    {'start': 25,
                                     'nibbles': 8,
                                     'type': 'ieee',
                                     'description': 'Tilt matrix element 6 '\
                                        '(H1Z)',
                                     'notes': ''
                                    }
                                ),
                                ('tilt_matrix_element_7',
                                    {'start': 29,
                                     'nibbles': 8,
                                     'type': 'ieee',
                                     'description': 'Tilt matrix element 7 '\
                                        '(H2Z)',
                                     'notes': ''
                                    }
                                )
                                ])
                        ),
                        ('32-byte Trace Header Block #7',
                            OrderedDict([('block_length_in_bytes', 32),
                                ('tilt_matrix_element_8',
                                    {'start': 1,
                                     'nibbles': 8,
                                     'type': 'ieee',
                                     'description': 'Tilt matrix element 8 '\
                                        '(VZ)',
                                     'notes': ''
                                    }
                                ),
                                ('azimuth_in_degress',
                                    {'start': 5,
                                     'nibbles': 8,
                                     'type': 'ieee',
                                     'description': 'Azimuth in degrees',
                                     'notes': ''
                                    }
                                ),
                                ('pitch_in_degrees',
                                    {'start': 9,
                                     'nibbles': 8,
                                     'type': 'ieee',
                                     'description': 'Pitch in degrees',
                                     'notes': ''
                                    }
                                ),
                                ('roll_in_degrees',
                                    {'start': 13,
                                     'nibbles': 8,
                                     'type': 'ieee',
                                     'description': 'Roll in degrees',
                                     'notes': ''
                                    }
                                ),
                                ('remote_unit_temperature',
                                    {'start': 17,
                                     'nibbles': 8,
                                     'type': 'ieee',
                                     'description': 'Remote unit temperature',
                                     'notes': ''
                                    }
                                ),
                                ('remote_unit_humidity',
                                    {'start': 21,
                                     'nibbles': 8,
                                     'type': 'ieee',
                                     'description': 'Remote unit humidity',
                                     'notes': ''
                                    }
                                )
                                ])
                        ),
                        ('32-byte Trace Header Block #8',
                            OrderedDict([('block_length_in_bytes', 32),
                                ('fairfield_test_analysis_code',
                                    {'start': 1,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Fairfield test analysis '\
                                        'code',
                                     'notes': ''
                                    }
                                ),
                                ('first_test_oscillator_attenuation',
                                    {'start': 5,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'First test oscillator '\
                                        'attenuation',
                                     'notes': ''
                                    }
                                ),
                                ('second_test_oscillator_attenuation',
                                    {'start': 9,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Second test oscillator '\
                                        'attenuation',
                                     'notes': ''
                                    }
                                ),
                                ('start_delay',
                                    {'start': 13,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Start delay (in '\
                                        'microseconds)',
                                     'notes': ''
                                    }
                                ),
                                ('dc_filter_flag',
                                    {'start': 17,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'DC filter flag',
                                     'notes': '0 - no filter\n1 - apply filter'
                                    }
                                ),
                                ('dc_filter_frequency',
                                    {'start': 21,
                                     'nibbles': 8,
                                     'type': 'ieee',
                                     'description': 'DC filter frequency',
                                     'notes': ''
                                    }
                                ),
                                ('preamp_path',
                                    {'start': 25,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Pre-amp path',
                                     'notes': '0 - external input selected '\
                                        '(default)\n1 - simulated data '\
                                        'selected\n2 - pre-amp input shorted '\
                                        'to ground\n3 - test oscillator with '\
                                        'sensors\n4 - test oscillator without '\
                                        'sensors\n5 - common mode test '\
                                        'oscillator with sensors\n6 - common '\
                                        'mode test oscillator without sensors'\
                                        '\n7 - test oscillator on positive '\
                                        'sensors with negative sensor grounded'\
                                        '\n8 - test oscillator on negative '\
                                        'sensors with positive sensor grounded'\
                                        '\n9 - test oscillator on positive PA '\
                                        'input with negative PA grounded\n10 '\
                                        '- test oscillator on negative PA '\
                                        'input with positive PA input inground'\
                                        '\n11 - test oscillator on positive '\
                                        'PA input with negative PA input '\
                                        'ground, no sensors\n12 - test '\
                                        'oscillator on negative PA input with '\
                                        'positive input ground, no sensors'

                                    }
                                ),
                                ('test_oscillator_signal_type',
                                    {'start': 29,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Test oscillator signal '\
                                        'type',
                                     'notes': '0 - test oscillator path open\n'\
                                        '1 - test signal selected\n2 - DC '\
                                        'reference selected\n3 - test '\
                                        'oscillator path grounded\n4 - DC '\
                                        'reference toggle selected'
                                    }
                                )
                                ])
                        ),
                        ('32-byte Trace Header Block #9',
                            OrderedDict([('block_length_in_bytes', 32),
                                ('test_signal_generator_type',
                                    {'start': 1,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Test signal generator '\
                                        'signal type',
                                     'notes': '0 - pattern is address ramp\n1 '\
                                        '- pattern is RU address ramp\n2 - '\
                                        'pattern is built from provided values'\
                                        '\n3 - pattern is random numbers\n4 - '\
                                        'pattern is a walking 1s\n5 - pattern '\
                                        'is a walking 0s\n6 - test signal is '\
                                        'a specified DC value\n7 - test '\
                                        'signal is a pulse train with '\
                                        'specified duty cycle\n8 - test '\
                                        'signal is a sine wave\n9 - test '\
                                        'signal is a dual tone sine\n10 - '\
                                        'test signal is an impulse\n11 - test '\
                                        'signal is a step function'
                                    }
                                ),
                                ('test_signal_generator_frequency_1',
                                    {'start': 5,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Test signal generator '\
                                        'frequency 1 (milliHertz)',
                                     'notes': ''
                                    }
                                ),
                                ('test_signal_generator_frequency_2',
                                    {'start': 9,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Test signal generator '\
                                        'frequency 2 (milliHertz)',
                                     'notes': ''
                                    }
                                ),
                                ('test_signal_generator_amplitude_1',
                                    {'start': 13,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Test signal generator '\
                                        'amplitude 1',
                                     'notes': 'In dB down from full scale, '\
                                        '-120 to +120, where the sign is used '\
                                        'to indicate the polarity'
                                    }
                                ),
                                ('test_signal_generator_amplitude_2',
                                    {'start': 17,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Test signal generator '\
                                        'amplitude 2',
                                     'notes': 'In dB down from full scale, '\
                                        '-120 to +120, where the sign is used '\
                                        'to indicate the polarity'
                                    }
                                ),
                                ('test_signal_generator_duty_cycle_in_percent',
                                    {'start': 21,
                                     'nibbles': 8,
                                     'type': 'ieee',
                                     'description': 'Test signal generator '\
                                        'duty cycle in %',
                                     'notes': ''
                                    }
                                ),
                                ('test_signal_generator_active_duration',
                                    {'start': 25,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Test signal active '\
                                        'duration (microseconds)',
                                     'notes': ''
                                    }
                                ),
                                ('test_signal_generator_activation_time',
                                    {'start': 29,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Test signal generator '\
                                        'activation time (microseconds)',
                                     'notes': ''
                                    }
                                )
                                ])
                        ),
                        ('32-byte Trace Header Block #10',
                            OrderedDict([('block_length_in_bytes', 32),
                                ('test_signal_generator_idle_level',
                                    {'start': 1,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Test signal generator '\
                                        'idle level (% full scale)',
                                     'notes': ''
                                    }
                                ),
                                ('test_signal_generator_active_level',
                                    {'start': 5,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Test signal generator '\
                                        'active level (% full scale)',
                                     'notes': ''
                                    }
                                ),
                                ('test_signal_generator_pattern_1',
                                    {'start': 9,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Test signal generator '\
                                        'pattern 1',
                                     'notes': 'Lower level 24 bits'
                                    }
                                ),
                                ('test_signal_generator_pattern_2',
                                    {'start': 13,
                                     'nibbles': 8,
                                     'type': 'binary',
                                     'description': 'Test signal generator '\
                                        'pattern 2',
                                     'notes': ''
                                    }
                                )
                                ])
                        )])
                )])

    def __init__(self, path, debug=False):
        self.path  = os.path.abspath(path)
        self.debug = debug
        self.segdfile = open(self.path, 'rb')
        #the byte number of the end of the last block read
        self.end_of_last_block = 0
        self.header_data = OrderedDict([])
        self.data = []
        #parse General Header blocks
        self.header_data['General Header'] = OrderedDict([])
        for header_block in self.schema['General Header']:
            self.header_data['General Header'][header_block] = \
                    self._read_header_block(self.schema['General Header']\
                                                       [header_block])
            self.end_of_last_block += \
                self.schema['General Header']\
                           [header_block]\
                           ['block_length_in_bytes']
        #parse Channel Set Descriptor blocks
        self.header_data['Channel Set Descriptor'] = OrderedDict([])
        for n in range(self.header_data['General Header']\
                                       ['General Header Block #1']\
                                       ['channel_sets_per_scan_type']\
                                       ['value']):
            self.header_data['Channel Set Descriptor']\
                        ['Channel Set Descriptor Block #%d' % (n + 1)] = \
                    self._read_header_block(
                            self.schema['Channel Set Descriptor']['Main Block'])
            self.end_of_last_block += self.schema['Channel Set Descriptor']\
                                                 ['Main Block']\
                                                 ['block_length_in_bytes']
        #parse the first three Extended Header blocks
        self.header_data['Extended Header'] = OrderedDict([])
        for n in range(3):
            header_block = '32-byte Extended Header Block #%d' % (n + 1)
            self.header_data['Extended Header'][header_block] = \
                    self._read_header_block(self.schema['Extended Header']\
                                                       [header_block])
            self.end_of_last_block += self.schema['Extended Header']\
                                             [header_block]\
                                             ['block_length_in_bytes']
        self.number_of_trace_blocks = self.header_data['Extended Header']\
                                      ['32-byte Extended Header Block #2']\
                                      ['number_of_records_in_file']\
                                      ['value']
        #parse the next n 32-byte Extended Header blocks as necessary
        for n in range(3, self.header_data['General Header']\
                                          ['General Header Block #2']\
                                          ['extended_header_blocks']\
                                          ['value']):
            header_block = '32-byte Extended Header auxiliary Block'
            block_label = '32-byte Extended Header Block #%d' % (n + 1)
            self.header_data['Extended Header'][block_label] = \
                    self._read_header_block(self.schema['Extended Header']\
                                                       [header_block])
            self.end_of_last_block += self.schema['Extended Header']\
                                                 [header_block]\
                                                 ['block_length_in_bytes']
        #parse the general External Header Block
        self.header_data['External Header'] = OrderedDict([])
        self.header_data['External Header']['External Header Block #1'] = \
                self._read_header_block(self.schema['External Header']\
                                                   ['External Header Block #1'])
        self.end_of_last_block += self.schema['External Header']\
                                             ['External Header Block #1']\
                                             ['block_length_in_bytes']
        #parse the next n 32-byte External Header blocks
        if self.header_data['General Header']\
                           ['General Header Block #1']\
                           ['number_of_32_byte_external_header_blocks']\
                           ['value'] == 'ff':
            number_of_32_byte_external_header_blocks = \
                    self.header_data['General Header']\
                                    ['General Header Block #2']\
                                    ['external_header_blocks']\
                                    ['value']
        else:
            number_of_32_byte_external_header_blocks = \
                self.header_data['General Header']\
                                ['General Header Block #1']\
                                ['number_of_32_byte_external_header_blocks']\
                                ['value']
        for n in range(number_of_32_byte_external_header_blocks - 1):
            self.header_data['External Header']\
                            ['32-byte External Header Block #%d' % (n + 1)] = \
                self._read_header_block(
                        self.schema['External Header']\
                                    ['32-byte External Header Auxiliary Block'])
            self.end_of_last_block += \
                    self.schema['External Header']\
                               ['32-byte External Header Auxiliary Block']\
                               ['block_length_in_bytes']

#    def __init__(self, path, debug=False):
#        self.path  = os.path.abspath(path)
#        self.debug = debug
#        self.segdfile = open(self.path, 'rb')
#        #the byte number of the end of the last block read
#        self.end_of_last_block = 0
#        self.header_data = OrderedDict([])
#        self.data = []
#        #parse General Header blocks
#        for header_block in self.schema['General Header']:
#            self._read_header_block('General Header',
#                    self.schema['General Header'][header_block],
#                    header_block)
#            self.end_of_last_block += \
#                self.schema['General Header']\
#                           [header_block]\
#                           ['block_length_in_bytes']
#        #parse Channel Set Descriptor blocks
#        for n in range(self.header_data['General Header']\
#                                       ['General Header Block #1']\
#                                       ['channel_sets_per_scan_type']\
#                                       ['value']):
#            self._read_header_block('Channel Set Descriptor',
#                   self.schema['Channel Set Descriptor']['Main Block'],
#                   'Channel Set Descriptor Block #%d' % (n + 1))
#            self.end_of_last_block += self.schema['Channel Set Descriptor']\
#                                                 ['Main Block']\
#                                                 ['block_length_in_bytes']
#        #parse the first three Extended Header blocks
#        for n in range(3):
#            header_block = '32-byte Extended Header Block #%d' % (n + 1)
#            self._read_header_block('Extended Header',
#                self.schema['Extended Header'][header_block],
#                header_block)
#            self.end_of_last_block += self.schema['Extended Header']\
#                                             [header_block]\
#                                             ['block_length_in_bytes']
#        self.number_of_trace_blocks = self.header_data['Extended Header']\
#                                      ['32-byte Extended Header Block #2']\
#                                      ['number_of_records_in_file']\
#                                      ['value']
#        #parse the next n 32-byte Extended Header blocks as necessary
#        for n in range(3, self.header_data['General Header']\
#                                          ['General Header Block #2']\
#                                          ['extended_header_blocks']\
#                                          ['value']):
#            header_block = '32-byte Extended Header auxiliary Block'
#            block_label = '32-byte Extended Header Block #%d' % (n + 1)
#            self._read_header_block('Extended Header',
#                    self.schema['Extended Header']\
#                               [header_block],
#                    block_label)
#            self.end_of_last_block += self.schema['Extended Header']\
#                                                 [header_block]\
#                                                 ['block_length_in_bytes']
#        #parse the general External Header Block
#        self._read_header_block('External Header',
#                self.schema['External Header']\
#                           ['External Header Block #1'],
#                'External Header Block #1')
#        self.end_of_last_block += self.schema['External Header']\
#                                             ['External Header Block #1']\
#                                             ['block_length_in_bytes']
#        #parse the next n 32-byte External Header blocks
#        if self.header_data['General Header']\
#                           ['General Header Block #1']\
#                           ['number_of_32_byte_external_header_blocks']\
#                           ['value'] == 'ff':
#            number_of_32_byte_external_header_blocks = \
#                    self.header_data['General Header']\
#                                    ['General Header Block #2']\
#                                    ['external_header_blocks']\
#                                    ['value']
#        else:
#            number_of_32_byte_external_header_blocks = \
#                self.header_data['General Header']\
#                                ['General Header Block #1']\
#                                ['number_of_32_byte_external_header_blocks']\
#                                ['value']
#        #for n in range(self.header_data['External Header']\
#        #                                  ['External Header Block #1']\
#        #                                  ['size']\
#        #                                  ['value']):
#        for n in range(number_of_32_byte_external_header_blocks - 1):
#            self._read_header_block('External Header',
#                    self.schema['External Header']\
#                               ['32-byte External Header Auxiliary Block'],
#                    '32-byte External Header Block #%d' % (n + 1))
#            self.end_of_last_block += \
#                    self.schema['External Header']\
#                               ['32-byte External Header Auxiliary Block']\
#                               ['block_length_in_bytes']


    def read_trace_block(self):
        header_data = OrderedDict([])
        for header_block in self.schema['Trace Header']:
            header_data[header_block] = \
                    self._read_header_block(self.schema['Trace Header']\
                                                       [header_block])
            self.end_of_last_block += self.schema['Trace Header']\
                                                 [header_block]\
                                                 ['block_length_in_bytes']
        nsamp = header_data['32-byte Trace Header Block #1']\
                           ['number_of_samples_per_trace']\
                           ['value']
        self.data = unpack('>%df' % nsamp, self.segdfile.read(nsamp * 4))
        self.end_of_last_block += nsamp * 4
        return nsamp

#    def read_trace_block(self):
#        for header_block in self.schema['Trace Header']:
#
#            self._read_header_block('Trace Header',
#                    self.schema['Trace Header'][header_block],
#                    header_block)
#            self.end_of_last_block += self.schema['Trace Header']\
#                                                 [header_block]\
#                                                 ['block_length_in_bytes']
#        nsamp = self.header_data['Trace Header']\
#                                ['32-byte Trace Header Block #1']\
#                                ['number_of_samples_per_trace']\
#                                ['value']
#        #data = self.segdfile.read(nsamp * 4)
#        self.data = unpack('>%df' % nsamp, self.segdfile.read(nsamp * 4))
#        self.end_of_last_block += nsamp * 4

#    def write_trace_block(self, tbl_wfdisc, args, datatype='sd'):
#        with trdestroying(trnew(None)) as tmpdb:
#            tr = tmpdb.schema_tables['trace']
#            with trfreeing(tr):
#                tr.record = tr.addnull()
#                tr.putv(('net', args['net']),
#                        ('sta', args['sta']),
#                        ('chan', args['chan']),
#                        ('time', args['time']),
#                        ('samprate', args['samprate']),
#                        ('calib', LEAST_SIGNIFICANT_COUNT))
#                if datatype == 'u4':
#                    tr.trputdata(self.data)
#                    tr.trsave_wf(tbl_wfdisc, append=True, datatype='u4')
#                elif datatype =='sd':
#                    #tr.trputdata([int(round(d / LEAST_SIGNIFICANT_COUNT))\
#                    #                for d in self.data])
#                    tr.trputdata(divide_through(self.data,
#                                                LEAST_SIGNIFICANT_COUNT))
#                    tr.trsave_wf(tbl_wfdisc, append=True, datatype='sd')

    def write_2_wfdisc(self, dbout, sta, ddir, dfile):
        general_header_block_1 = self.header_data['General Header']\
                                                 ['General Header Block #1']
        year = general_header_block_1['first_shot_last_two_digits_of_year']\
                                     ['value']
        year = int('20%d' % year)
        jday = general_header_block_1['first_shot_julian_day']\
                                     ['value']
        utc_time = general_header_block_1['first_shot_UTC_time']\
                                          ['value']
        utc_time = str('%06d' % utc_time)
        time = str2epoch('%d%d %d:%d:%d' % (year,
                                            jday,
                                            int(utc_time[:2]),
                                            int(utc_time[2:4]),
                                            int(utc_time[4:])))
        if not os.path.isfile(dbout):
            dbcreate(dbout, 'css3.0')
        with closing(dbopen(dbout, 'r+')) as db:
            tbl_wfdisc = db.schema_tables['wfdisc']
            for i in range(self.number_of_trace_blocks):
                if i == self.number_of_trace_blocks - 1:
                    self.end_of_last_block += 20
                    header_block = self._read_header_block(
                            self.schema['Trace Header']\
                                       ['32-byte Trace Header Block #1'])
                    nsamp = header_block['number_of_samples_per_trace']\
                                        ['value']
                    self.end_of_last_block += 320
                else:
                    self.end_of_last_block += 340
                    nsamp = 131 * 500
                tbl_wfdisc.record = tbl_wfdisc.addnull()
                tbl_wfdisc.putv(('sta', sta),
                                ('chan', 'HHZ'),
                                ('calib', (1.0 / LEAST_SIGNIFICANT_COUNT)),
                                ('dir', ddir),
                                ('dfile', dfile),
                                ('foff', self.end_of_last_block),
                                ('nsamp', nsamp),
                                ('samprate', 500.0),
                                ('time', time),
                                ('datatype', 't4'),
                                ('endtime', time + ((nsamp - 1) * (1.0 / 500.0))))
                time += 131
                self.end_of_last_block += nsamp * 4


    def close(self):
        self.segdfile.close()

    def __str__(self):
        """
        Return the string representation of self.
        """
        s = 'SEG-D Header contents\n---------------------\n'
        for general_block in self.header_data:
            s = '%s\t%s\n\t%s\n' % (s, general_block, '-' * len(general_block))
            for header_block in self.header_data[general_block]:
                s = '%s\t\t%s\n\t\t%s\n' % (s, header_block, '-' * \
                        len(header_block))
                for field in self.header_data[general_block][header_block]:
                    if field == 'block_length_in_bytes': continue
                    s = '%s\t\t%s: %s\n' \
                            % (s,
                            self.header_data[general_block]\
                                            [header_block]\
                                            [field]\
                                            ['description'],
                            self.header_data[general_block]\
                                            [header_block]\
                                            [field]\
                                            ['value'])
                            #getattr(self, field))
                s = '%s\n' % s
        return s

    def _write_to_file(self, path):
        """
        Return the string representation of self.
        """
        outfile = open(path, 'w')
        outfile.write('SEG-D Header contents\n---------------------\n')
        for general_block in self.header_data:
            outfile.write('\t%s\n\t%s\n' % (general_block, '-' * \
                    len(general_block)))
            for header_block in self.header_data[general_block]:
                outfile.write('\t\t%s\n\t\t%s\n' % (header_block, '-' * \
                        len(header_block)))
                for field in self.header_data[general_block][header_block]:
                    if field == 'block_length_in_bytes': continue
                    outfile.write('\t\t%s: %s\n' \
                            % (self.header_data[general_block]\
                                                [header_block]\
                                                [field]\
                                                ['description'],
                              self.header_data[general_block]\
                                              [header_block]\
                                              [field]\
                                              ['value']))
                            #getattr(self, field))
                outfile.write('\n')
        outfile.close()

    def info(self):
        """
        Method to print nicely the information contained in the object.
        """

        print ("*segd*:\tsegd.type() => %s" % self.type)
        print ("*segd*:\tsegd.path() => %s" % self.path)
        print ("*segd*:\tsegd.list() => %s" % self.list())
        for element in sorted(self.dbs):
            print ("*segd*:\t%s => %s" % (element,self.dbs[element]['times']))


    def __call__(self):
        """
        Method to intercepts data requests.
        """

        self.info()
        return False


    def __del__(self):
        """
        Method to clean database objects.
        """

        self.dbs = {}


    def _problem(self, log):
        """
        Method to print problems and raise exceptions
        """
        raise SegDException('*segd*: ERROR=> %s' % log)


    def _get_list(self):
        """
        Private method.
        """
        pass


    def list(self):
        """
        Method to list items.
        """

        try:
            return self.dbs.keys()
        except:
            raise SegDException('*segd*: ERROR=> Cannot check content of list!')


    def purge(self,tbl=None):
        """
        Method to clean object.
        """
        pass

    def _read_header_block(self, block_schema):
        """
        Read a header block and update self with data extracted from header.

        Arguments:
        general_block - the name of the containing header block
        (General Header, Extended Header etc...)

        block_schema - the schema of the sub-block to be parsed

        block_label - a unique storage label for header data from that
        sub-block
        """
        return_dict = OrderedDict([])
        for field in block_schema:
            if field == 'block_length_in_bytes': continue
            if block_schema[field]['type'] == 'bcd':
                value = self._read_BCD(block_schema[field]['start'],
                                       block_schema[field]['nibbles'])
            elif block_schema[field]['type'] == 'binary':
                value = self._read_binary(block_schema[field]['start'],
                                          block_schema[field]['nibbles'])
            elif block_schema[field]['type'] == 'ieee':
                value = self._read_ieee(block_schema[field]['start'],
                                         block_schema[field]['nibbles'])
            else:
                self._problem('Data type %s not valid' \
                        % block_schema[field]['type'])
            return_dict[field] = {'value': value,
                        'description': block_schema[field]['description']}
        return return_dict

#    def _read_header_block(self, general_block, block_schema, block_label):
#        """
#        Read a header block and update self with data extracted from header.
#
#        Arguments:
#        general_block - the name of the containing header block
#        (General Header, Extended Header etc...)
#
#        block_schema - the schema of the sub-block to be parsed
#
#        block_label - a unique storage label for header data from that
#        sub-block
#        """
#        if general_block not in self.header_data:
#            self.header_data[general_block] = OrderedDict([])
#        if block_label not in self.header_data[general_block]:
#            self.header_data[general_block][block_label] = OrderedDict([])
#        for field in block_schema:
#            if field == 'block_length_in_bytes': continue
#            if block_schema[field]['type'] == 'bcd':
#                value = self._read_BCD(block_schema[field]['start'],
#                                       block_schema[field]['nibbles'])
#            elif block_schema[field]['type'] == 'binary':
#                value = self._read_binary(block_schema[field]['start'],
#                                          block_schema[field]['nibbles'])
#            elif block_schema[field]['type'] == 'ieee':
#                value = self._read_ieee(block_schema[field]['start'],
#                                         block_schema[field]['nibbles'])
#            else:
#                self._problem('Data type %s not valid' \
#                        % block_schema[field]['type'])
#            self.header_data[general_block][block_label][field] = \
#                    {'value': value,
#                        'description': block_schema[field]['description']}

    def _read_BCD(self, start, nibbles):
        """
        Read BCD nibbles from file and return integer value.

        Arguments:
        start - the byte index of the starting nibble for the data field
        relative to the start of the header block

        nibbles - the number of nibbles of BCD data to be read

        Returns:
        return_data - the integer value represented by the BCD data

        Caveats:
        This method will return a string value when the BCD data does
        not convert to a integer value.
        """
        data,\
        ignore_first_nibble,\
        ignore_last_nibble,\
        n_bytes = self._get_raw_data(start, nibbles)
        is_first_byte, byte_count = True, 0
        unpacked_data = []
        for char in data:
            byte_count += 1
            char = ord(char)
            #unpack the first nibble of the byte, unless this is the
            #first byte, and the first nibble is to be ignored
            if not (is_first_byte and ignore_first_nibble):
                unpacked_data += ['%x' % (char >> 4)]
            #unpack the second nibble of the byte, unless this is the
            #last byte, and the last nibble is to be ignored
            if not (byte_count == n_bytes and ignore_last_nibble):
                unpacked_data += ['%x' % (char & 0xF)]
            is_first_byte = False
        return_data = ''
        for char in unpacked_data:
            return_data = '%s%s' % (return_data, char)
        try:
            return_data = int(return_data)
        except ValueError:
            pass
        return return_data

    def _read_binary(self, start, nibbles):
        """
        Unpack binary integer from file.

        Arguments:
        start - the byte index of the starting nibble for the data
        chunk to be read, relative to the beginning of the header block

        nibbles - the number of nibbles of data to be read

        Returns:
        return_data - integer value
        """
        data,\
        ignore_first_nibble,\
        ignore_last_nibble,\
        n_bytes = self._get_raw_data(start, nibbles)
        if n_bytes not in range(8):
            #self._problem('_read_binary() cannot read more than 4 '\
            #              'bytes of data at once.')
            return 0
        if n_bytes == 1:
            return_data = int(unpack('>B', data)[0])
            if ignore_first_nibble: return_data = return_data & 0x0F
            if ignore_last_nibble: return_data = return_data >> 4
            return return_data
        elif n_bytes == 2:
            return_data = int(unpack('>H', data)[0])
            if ignore_first_nibble: return_data = return_data & 0x0FFF
            if ignore_last_nibble: return_data = return_data >> 4
            return return_data
        elif n_bytes == 3 or n_bytes == 4:
            if n_bytes == 3: data = zero_pad(data, 4)
            return_data = int(unpack('>I', data)[0])
            if ignore_first_nibble: return_data = return_data & 0x0FFFFFFF
            if ignore_last_nibble: return_data = return_data >> 4
        elif n_bytes > 4:
            if n_bytes != 8: data = zero_pad(data, 8)
            return_data = int(unpack('>Q', data)[0])
            if ignore_first_nibble: return_data = \
                    return_data & 0x0FFFFFFFFFFFFFFF
            if ignore_last_nibble: return_data = return_data >> 4
        return return_data


    def _read_ieee(self, start, nibbles):
        """
        Unpack IEEE float from file.

        Arguments:
        start - the byte index of the starting nibble for the data
        chunk to be read, relative to the beginning of the header block

        nibbles - the number of nibbles of data to be read

        Returns:
        return_data - float value
        """
        data,\
        ignore_first_nibble,\
        ignore_last_nibble,\
        n_bytes = self._get_raw_data(start, nibbles)
        if n_bytes == 4:
            return_data = float(unpack('>f', data)[0])
        elif n_bytes == 8:
            return_data = float(unpack('>d', data)[0])
        else:
            return_data = None
        return return_data

    def _get_raw_data(self, start, nibbles):
        """
        Read and return raw data from file SEG-D file.

        Arguments:
        start - the byte index of the starting nibble for the data
        chunk to be read, relative to the beginning of the header block

        nibbles - the number of nibbles of data to be read

        Returns:
        data - the raw data requested

        ignore_first_nibble - a flag indicating whether or not to
        ignore the first nibble of data

        ignore_last_nibble - a flag indicating whether or not to ignore
        the last nibble

        n_bytes - the number of bytes of data returned
        """
        ignore_first_nibble, ignore_last_nibble = False, False
        #if the data field terminates at the middle of a byte,
        #create a flag to ignore the last nibble of data
        if (start + nibbles / 2.0) % 1 != 0: ignore_last_nibble = True
        #if the data begins at the middle of a byte,
        #create a flag to ignore the first nibble
        if start % 1 != 0:
            ignore_first_nibble = True
            #move the starting byte index to the beginning of the byte
            start = start - 0.5
        #determine the number of bytes to read
        if nibbles % 2 == 1: n_bytes = (nibbles + 1) / 2
        else: n_bytes = nibbles / 2
        self.segdfile.seek(self.end_of_last_block + start - 1)
        data = self.segdfile.read(n_bytes)
        return data, ignore_first_nibble, ignore_last_nibble, n_bytes

def zero_pad(s, size):
    """
    Pad a hex-string with leading zeroes until string is 'size' bytes.
    Return padded string.
    """
    if len(s) == size:
        return s
    else:
        while len(s) != size:
            s = '\x00%s' % s
    return s

#def _parse_args():
#    from argparse import ArgumentParser
#    parser = ArgumentParser()
#    parser.add_argument('dbout', type=str, help='Output database name.')
#    parser.add_argument('data_dir', type=str, help='Input data directory.')
#    return parser.parse_args()

#if __name__ == '__main__':
#    """
#    This will run if the file is called directly.
#    """
#    args = _parse_args()
#    working_dir = os.getcwd()
#    for a_file in sorted(os.listdir(args.data_dir)):
#        print 'Processing file: %s' % a_file
#        #need a temporary databse to write data out before compressing
#        #using trexcerpt
#        tmp_db_dir = os.path.join(os.getcwd(), 'tmp_segd2db')
#        #if a pre-existing temporary database is found, remove it
#        if os.path.exists(tmp_db_dir):
#            try:
#                shutil.rmtree(tmp_db_dir)
#            except OSError:
#                sys.exit('Could not remove pre-existing temporary database '\
#                         'directory in working directory. Check permissions.')
#        #create a new temporary database directory
#        try:
#            os.mkdir(tmp_db_dir)
#        except OSError:
#            sys.exit('Could not create temporary database directory in working '\
#                     'directory. Check permissions.')
#        #create a temporary database
#        tmp_db_path = os.path.join(tmp_db_dir, 'tmp')
#        try:
#            dbcreate(tmp_db_path, 'css3.0')
#        except DbcreateError:
#            sys.exit('Could not create temporary database in temporary '\
#                     'directory. Check permissions.')
#        #write the SegD file to temporary database
#        sta = a_file.split('.')[0]
#        print '%s - Reading SEG-D header data.' % sta
#        segd = SegD(os.path.join(args.data_dir, a_file))
#        wfargs = {'net': 'SGBF',
#                  'sta': sta,
#                  'chan': 'HHZ'}
#        general_header_block_1 = segd.header_data['General Header']\
#                                                 ['General Header Block #1']
#        year = general_header_block_1['first_shot_last_two_digits_of_year']\
#                                     ['value']
#        year = int('20%d' % year)
#        jday = general_header_block_1['first_shot_julian_day']\
#                                     ['value']
#        utc_time = general_header_block_1['first_shot_UTC_time']\
#                                         ['value']
#        utc_time = str('%06d' % utc_time)
#        time = str2epoch('%d%d %d:%d:%d' % (year,
#                                            jday,
#                                            int(utc_time[:2]),
#                                            int(utc_time[2:4]),
#                                            int(utc_time[4:])))
#        wfargs['time'] = time
#        record_length = segd.header_data['General Header']\
#                                        ['General Header Block #2']\
#                                        ['extended_record_length_in_milliseconds']\
#                                        ['value']
#        record_length /= 1000.0
#        with closing(dbopen(tmp_db_path, 'r+')) as db:
#            tbl_wfdisc = db.schema_tables['wfdisc']
#            for i in range(segd.number_of_trace_blocks):
#                print '%s - Converting trace block starting at: %s' \
#                        % (sta, epoch2str(wfargs['time'], '%Y%j %H:%M:%S.%s'))
#                #raw_input('\tRead trace block')
#                segd.read_trace_block()
#                nsamp = segd.header_data['Trace Header']\
#                                        ['32-byte Trace Header Block #1']\
#                                        ['number_of_samples_per_trace']\
#                                        ['value']
#                wfargs['samprate'] = nsamp / record_length
#                #raw_input('\tWrite trace block')
#                segd.write_trace_block(tbl_wfdisc, wfargs, datatype='sd')
#                wfargs['time'] += record_length
#        segd.close()
#        start = int('%d%d' % (year, jday))
#        end = int(epoch2str(wfargs['time'], '%Y%j'))
#        #navigate to output db directory
#        os.chdir(os.path.dirname(args.dbout))
#        #Use trexcerpt to condense data into final database
#        for tstart in range(start, end + 1):
#            cmd = ['trexcerpt', '-a', '-D', '-E',
#                    '-w', '%Y/%{sta}/%Y%j_%{sta}.msd',
#                   tmp_db_path, args.dbout,
#                   str(tstart), str(tstart + 1)]
#            print '%s - %s' % (sta, ' '.join(cmd))
#            if subprocess.call(cmd):
#                sys.exit('trexcerpt command failed...\n%s' % ' '.join(cmd))
#        os.chdir(working_dir)
#    #clean up temporary database directory
#    try:
#        shutil.rmtree(tmp_db_dir)
#    except OSError:
#        sys.exit('Could not remove pre-existing temporary database '\
#                 'directory in working directory. Check permissions.')

def _parse_args():
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('dbout', type=str, help='Output database name.')
    parser.add_argument('data_file', type=str, help='Data file.')
    return parser.parse_args()

if __name__ == '__main__':
    """
    This will run if the file is called directly.
    """
    args = _parse_args()
    working_dir = os.getcwd()
    a_file = args.data_file
    print ('Processing file: %s' % a_file)
    #need a temporary database to write data out before compressing
    #using trexcerpt
    tmp_db_dir = os.path.join(os.getcwd(), 'tmp_segd2db')
    #if a pre-existing temporary database is found, remove it
    if os.path.exists(tmp_db_dir):
        try:
            shutil.rmtree(tmp_db_dir)
        except OSError:
            sys.exit('Could not remove pre-existing temporary database '\
                     'directory in working directory. Check permissions.')
    #create a new temporary database directory
    try:
        os.mkdir(tmp_db_dir)
    except OSError:
        sys.exit('Could not create temporary database directory in working '\
                 'directory. Check permissions.')
    #create a temporary database
    tmp_db_path = os.path.join(tmp_db_dir, 'tmp')
    try:
        dbcreate(tmp_db_path, 'css3.0')
    except DbcreateError:
        sys.exit('Could not create temporary database in temporary '\
                 'directory. Check permissions.')
    #write the SegD file to temporary database
    sta = os.path.basename(a_file).split('.')[0]
    print ('%s - Reading SEG-D header data.' % sta)
    segd = SegD(os.path.join(a_file))
    wfargs = {'net': 'SGBF',
              'sta': sta,
              'chan': 'HHZ'}
    general_header_block_1 = segd.header_data['General Header']\
                                             ['General Header Block #1']
    year = general_header_block_1['first_shot_last_two_digits_of_year']\
                                 ['value']
    year = int('20%d' % year)
    jday = general_header_block_1['first_shot_julian_day']\
                                 ['value']
    utc_time = general_header_block_1['first_shot_UTC_time']\
                                     ['value']
    utc_time = str('%06d' % utc_time)
    time = str2epoch('%d%d %d:%d:%d' % (year,
                                        jday,
                                        int(utc_time[:2]),
                                        int(utc_time[2:4]),
                                        int(utc_time[4:])))
    wfargs['time'] = time
    record_length = segd.header_data['General Header']\
                                    ['General Header Block #2']\
                                    ['extended_record_length_in_milliseconds']\
                                    ['value']
    record_length /= 1000.0


    with closing(dbopen(tmp_db_path, 'r+')) as db:
        tbl_wfdisc = db.schema_tables['wfdisc']

        with trdestroying(trnew(None)) as tmpdb:
            tr = tmpdb.schema_tables['trace']
            tr.record = tr.addnull()
            tr.putv(('net', wfargs['net']),
                    ('sta', wfargs['sta']),
                    ('chan', wfargs['chan']),
                    ('calib', LEAST_SIGNIFICANT_COUNT))

            for i in range(segd.number_of_trace_blocks):
                print ('%s - Converting trace block starting at: %s' % (
                        sta, epoch2str(wfargs['time'], '%Y%j %H:%M:%S.%s')))
                nsamp = segd.read_trace_block()
                #nsamp = segd.header_data['Trace Header']\
                #        ['32-byte Trace Header Block #1']\
                #        ['number_of_samples_per_trace']\
                #        ['value']
                wfargs['samprate'] = nsamp / record_length
                #segd.write_trace_block(tbl_wfdisc, wfargs, datatype='sd')
                tr.putv(('time',     wfargs['time']),
                        ('samprate', wfargs['samprate']))
                data = tuple([int(round(d / LEAST_SIGNIFICANT_COUNT)) \
                    for d in segd.data])
                tr.trputdata(data)

                # Update for next loop
                wfargs['time'] += record_length

                tr.trsave_wf(tbl_wfdisc, append=True, datatype='sd')

    segd.close()

    start = int('%d%d' % (year, jday))
    end = int(epoch2str(wfargs['time'], '%Y%j'))
    #navigate to output db directory
    os.chdir(os.path.dirname(args.dbout))
    #Use trexcerpt to condense data into final database
    for tstart in range(start, end + 1):
        cmd = ['trexcerpt', '-a', '-D', '-E',
                '-w', '%Y/%{sta}/%Y%j_%{sta}.msd',
               tmp_db_path, args.dbout,
               str(tstart), str(tstart + 1)]
        print ('%s - %s' % (sta, ' '.join(cmd)))
        if subprocess.call(cmd):
            sys.exit('trexcerpt command failed...\n%s' % ' '.join(cmd))
    os.chdir(working_dir)

    #clean up temporary database directory
    try:
        shutil.rmtree(tmp_db_dir)
    except OSError:
        sys.exit('Could not remove pre-existing temporary database '\
                'directory in working directory. Check permissions.')
