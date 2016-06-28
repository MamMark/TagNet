from construct import *

try:
    bytes
except NameError:
    bytes = str

#################################################################
#
# Enumerations defined
#
def Si446xCmds_t(code):
    return Enum(code,
                NOP                    = 0,
                POWER_UP               = 0x02,
                PART_INFO              = 0x01,
                FUNC_INFO              = 0x10,
                SET_PROPERTY           = 0x11,
                GET_PROPERTY           = 0x12,
                GPIO_PIN_CFG           = 0x13,
                FIFO_INFO              = 0x15,
                GET_INT_STATUS         = 0x20,
                REQUEST_DEVICE_STATE   = 0x33,
                CHANGE_STATE           = 0x34,
                READ_CMD_BUFF          = 0x44,
                FRR_A_READ             = 0x50,
                FRR_B_READ             = 0x51,
                FRR_C_READ             = 0x53,
                FRR_D_READ             = 0x57,
                IRCAL                  = 0x17,
                IRCAL_MANUAL           = 0x1a,
                START_TX               = 0x31,
                WRITE_TX_FIFO          = 0x66,
                PACKET_INFO            = 0x16,
                GET_MODEM_STATUS       = 0x22,
                START_RX               = 0x32,
                RX_HOP                 = 0x36,
                READ_RX_FIFO           = 0x77,
                GET_ADC_READING        = 0x14,
                GET_PH_STATUS          = 0x21,
                GET_CHIP_STATUS        = 0x23,
            )
#end def

def Si446xPropGroups_t(subcon):
    return Enum(subcon,
                GLOBAL                 = 0x00,
                INT_CTL                = 0x01,
                FRR_CTL                = 0x02,
                PREAMBLE               = 0x10,
                SYNC                   = 0x11,
                PKT                    = 0x12,
                MODEM                  = 0x20,
                MODEM_CHFLT            = 0x21,
                PA                     = 0x22,
                SYNTH                  = 0x23,
                MATCH                  = 0x30,
                FREQ_CONTROL           = 0x40,
                RX_HOP                 = 0x50,
            )
#end def

def Si446xFrrCtlMode_t(subcon):
    return Enum(subcon,
                DISABLED               = 0,
                INT_PH_PEND            = 4,
                INT_MODEM_PEND         = 6,
                CURRENT_STATE          = 9,
                LATCHED_RSSI           = 10,
                _default_              = 0,
            )
#end def
 
def Si446xNextStates_t(subcon):
    return Enum(subcon,
                NOCHANGE               = 0,
                SLEEP                  = 1,
                SPI_ACTIVE             = 2,
                READY                  = 3,
                READY2                 = 4,
                TX_TUNE                = 5,
                RX_TUNE                = 6,
                TX                     = 7,
                RX                     = 8,
                _default_              = 0,
            )
#end def

#################################################################
#
# structures defined to encode/decode packet format

#
group_s = Struct('group_s',
                 Si446xCmds_t(UBInt8("cmd")),
                 Byte('group'),
                 Byte('num_props'),
                 Byte('start_prop'),
             )

#
change_state_cmd_s = Struct('change_state_cmd_s',
                            Si446xCmds_t(UBInt8("cmd")),
                            Byte('state'),
                        )

#
change_state_rsp_s = Struct('change_state_rsp_s',
                            Byte('cts'),
                        )

#
config_frr_cmd_s = Struct('config_frr_cmd_s',
                          Embedded(group_s),
                          Si446xFrrCtlMode_t(Byte('a_mode')),
                          Si446xFrrCtlMode_t(Byte('b_mode')),
                          Si446xFrrCtlMode_t(Byte('c_mode')),
                          Si446xFrrCtlMode_t(Byte('d_mode')),
                      )

#
fifo_info_cmd_s = Struct('fifo_info_cmd_s',
                         Si446xCmds_t(UBInt8("cmd")),
                         BitStruct('state',
                                   Padding(6),
                                   Flag('rx'),
                                   Flag('tx'),
                               ),
                    )

#
fifo_info_rsp_s = Struct('fifo_info_rsp_s',
                         Byte('cts'),
                         Byte('rx_fifo_count'),
                         Byte('tx_fifo_space'),
                    )

#
get_property_cmd_s = Struct('get_property_cmd_s',
                            Embedded(group_s),
                        )

#
get_property_rsp_s = Struct('get_property_rsp_s',
                            Byte('cts'),
                            Field('data', lambda ctx: 16)
                       )

#
packet_info_cmd_s = Struct('power_up_cmd_s',
                           Si446xCmds_t(UBInt8("cmd")),
                           BitStruct('field',
                                     Padding(2),
                                     Enum(BitField('field_number',6),
                                          NO_OVERRIDE = 0,
                                          PKT_FIELD_1 = 1,
                                          PKT_FIELD_2 = 2,
                                          PKT_FIELD_3 = 4,
                                          PKT_FIELD_4 = 8,
                                          PKT_FIELD_5 = 16,
                                      )
                                 )
                       )

#
packet_info_rsp_s = Struct('power_up_rsp_s',
                           Byte('cts'),
                           UBInt16('length'),
                       )

# command=
# ox00  cmd=Si446xCmds.POWER_UP
# ox01  boot_options=[patch(7)patch=NO_PATCH(0), (5:0)FUNC=PRO(1)]
# 0x02  xtal_options=[(0)TCXO=XTAL(0)]
# 0x03  xofreq=0x01C9C380  x0[31:24]
# 0x04                     XO_FREQ[23:16]
# 0x05                     XO_FREQ[15:8]
# 0x06                     XO_FREQ[7:0]
# response=
# 0x00  cts=  0xff=NOT_READY
#
power_up_cmd_s = Struct('power_up_cmd_s',
                        Si446xCmds_t(UBInt8("cmd")),
                        BitStruct('boot_options',
                                  Flag('patch'),
                                  Padding(1),
                                  BitField('func',6)
                              ),
                        BitStruct('xtal_options',
                                  Padding(6),
                                  BitField('txcO', 2)
                              ),
                        UBInt32('xo_freq')
                    )

#
read_cmd_s = Struct('read_cmd_s',
                    Si446xCmds_t(UBInt8("cmd")
                ),
)

#
read_cmd_buff_rsp_s = Struct('read_cmd_buff_rsp_s',
                             Byte('cts'),
                             Field('cmd_buff', lambda ctx: 15)
                         )

#
read_func_info_rsp_s = Struct('read_func_info_rsp_s',
                              Byte('cts'),
                              Byte('revext'),
                              Byte('revbranch'),
                              Byte('revint'),
                              UBInt16('patch'),
                              Byte('func'),
                          )

#
read_part_info_rsp_s = Struct('read_part_info_rsp_s',
                              Byte('cts'),
                              Byte('chiprev'),
                              UBInt16('part'),
                              Byte('pbuild'),
                              UBInt16('id'),
                              Byte('customer'),
                              Byte('romid'),
                          )

#
set_property_cmd_s = Struct('set_property_cmd_s',
                            Embedded(group_s),
                        )

#
start_rx_cmd_s = Struct('start_rx_cmd_s',
                        Si446xCmds_t(UBInt8("cmd")),
                        Byte('channel'),
                        BitStruct('condition',
                                  Padding(6),
                                  Enum(Field('start',2),
                                       IMMEDIATE = 0,
                                       WUT = 1,
                                   ),
                              ),
                        UBInt16('rx_len'),
                        Si446xNextStates_t(Byte("next_state1")),
                        Si446xNextStates_t(Byte("next_state2")),
                        Si446xNextStates_t(Byte("next_state3")),
                    )

#
start_tx_cmd_s = Struct('start_tx_cmd_s',
                        Si446xCmds_t(UBInt8("cmd")),
                        Byte('channel'),
                        BitStruct('condition',
                                  Enum(BitField('txcomplete_state',4),
                                       NOCHANGE = 0,
                                       SLEEP = 1,
                                       SPI_ACTIVE = 2,
                                       READY = 3,
                                       READY2 = 4,
                                       TX_TUNE = 5,
                                       RX_TUNE = 6,
                                       RX = 8,
                                   ),
                                  Padding(1),
                                  Enum(BitField('retransmit',1),
                                       NO = 0,
                                       YES = 1,
                                   ),
                                  Enum(BitField('start',2),
                                       IMMEDIATE = 0,
                                       WUT = 1,
                                   ),
                              ),
                        UBInt16('tx_len'),
                    )


#################################################################
#
# Radio Property Group definitions
#
global_group_s = Struct('global_group',
                        Byte('xo_tune'),
                        Byte('clk_cfg'),
                        Byte('low_batt_thresh'),
                        Byte('config'),
                        Byte('wut_config'),
                        UBInt16('wut_m'),
                        Byte('wut_r'),
                        Byte('wut_ldc'),
                        Byte('wut_cal'),
                    )

int_ctl_group_s = Struct('int_ctl_group',
                        Byte('enable'),
                        Byte('ph_enable'),
                        Byte('modem_enable'),
                        Byte('chip_enable'),
                        )

frr_ctl_group_s = Struct('frr_ctl_group',
                          Si446xFrrCtlMode_t(Byte('a_mode')),
                          Si446xFrrCtlMode_t(Byte('b_mode')),
                          Si446xFrrCtlMode_t(Byte('c_mode')),
                          Si446xFrrCtlMode_t(Byte('d_mode')),
                        )

preamble_group_s = Struct('_group',
                        Byte('tx_length'),
                        Byte('config_std_1'),
                        Byte('config_nstd'),
                        Byte('config_std_2'),
                        Byte('config'),
                        UBInt32('pattern'),
                        Byte('postamble_config'),
                        UBInt32('postamble_pattern'),
                        )

sync_group_s = Struct('_group',
                        Byte('config'),
                        UBInt32('bits'),
                        )

pkt_field_s = Struct('pkt_field',
                        UBInt16('length'),
                        Byte('config'),
                        Byte('crc_config'),
                    )
pkt_group_s = Struct('pkt_group',
                     Byte('crc_config'),
                     UBInt16('wht_poly'),
                     UBInt16('wht_seed'),
                     Byte('wht_bit_num'),
                     Byte('config1'),
                     Byte('len'),
                     Byte('len_field_source'),
                     Byte('len_adjust'),
                     Byte('tx_threshold'),
                     Byte('rx_threshold'),
                     Array(5, pkt_field_s),
                     Array(5, pkt_field_s),
                    )

modem_group_s = Struct('modem_group',
                       Byte('mod_type'),
                       Byte('map_control'),
                       Byte('dsm_ctrl'),
                       BitField('data_rate', 3),
                       UBInt32('tx_nco_mode'),
                       BitField('freq_dev', 3),
                       UBInt16('freq_offset'),
                       Array(9, UBInt8('filter_coeff')),
                       Byte('tx_ramp_delay'),
                       Byte('mdm_ctrl'),
                       Byte('if_control'),
                       BitField('if_freq',3),
                       Byte('decimation_cfg1'),
                       Byte('decimation_cfg0'),
                       Padding(2),
                       UBInt16('bcr_osr'),
                       BitField('bcr_nco_offset',3),
                       UBInt16('bcr_gain'),
                       Byte('bcr_gear'),
                       Byte('bcr_misc1'),
                       Byte('bcr_misc0'),
                       Byte('afc_gear'),
                       Byte('afc_wait'),
                       UBInt16('afc_gain'),
                       UBInt16('afc_limiter'),
                       Byte('afc_misc'),
                       Byte('afc_zipoff'),
                       Byte('adc_ctrl'),
                       Byte('agc_control'),
                       Padding(2),
                       Byte('agc_window_size'),
                       Byte('agc_rffpd_decay'),
                       Byte('agc_ifpd_decay'),
                       Byte('fsk4_gain1'),
                       Byte('fsk4_gain0'),
                       UBInt16('fsk4_th'),
                       Byte('fsk4_map'),
                       Byte('ook_pdtc'),
                       Byte('ook_blopk'),
                       Byte('ook_cnt1'),
                       Byte('ook_misc'),
                       Byte('raw_search'),
                       Byte('raw_control'),
                       UBInt16('raw_eye'),
                       Byte('ant_div_mode'),
                       Byte('ant_div_control'),
                       Byte('rssi_thresh'),
                       Byte('rssi_jump_thesh'),
                       Byte('rssi_control'),
                       Byte('rssi_control2'),
                       Byte('rssi_comp'),
                       Padding(1),
                       Byte('clkgen_band'),
                       )

modem_chflt_group_s = Struct('modem_chflt_group',
                        BitField('chflt_rx1_chflt_coe', 18),
                        BitField('chflt_rx2_chflt_coe', 18),
                        )

pa_group_s = Struct('pa_group',
                        Byte('mode'),
                        Byte('pwr_lvl'),
                        Byte('bias_clkduty'),
                        Byte('tc'),
                        Byte('ramp_ex'),
                        Byte('ramp_down_delay'),
                        )

synth_group_s = Struct('synth_group',
                       Byte('pfdcp_cpff'),
                       Byte('pfdcp_cpint'),
                       Byte('vco_kv'),
                       Byte('lpfilt3'),
                       Byte('lpfilt2'),
                       Byte('lpfilt1'),
                       Byte('lpfilt0'),
                       Byte('vco_kvcal'),
                       )

match_field_s = Struct('match_field',
                       Byte('value'),
                       Byte('mask'),
                       Byte('ctrl'),
                       )
match_group_s = Struct('match_group',
                       Array(4, match_field_s),
#                       Rename("m1", match_field_s),
#                       Rename("m2", match_field_s),
#                       Rename("m3", match_field_s),
#                       Rename("m4", match_field_s),
                       )

freq_control_group_s = Struct('freq_control_group',
                        Byte('inte'),
                        BitField('frac', 3),
                        UBInt16('channel_step_size'),
                        Byte('w_size'),
                        Byte('vcocnt_rx_adj'),
                        )

rx_hop_group_s = Struct('rx_hop_group',
                        Byte('control'),
                        Byte('table_size'),
                        Array(64, Byte('table_entry')),
                        )

radio_config_groups_s = {
    "global": global_group_s,
    "frr_ctl": frr_ctl_group_s,
    "preamble": preamble_group_s,
    "sync": sync_group_s,
    "pkt": pkt_group_s,
    "modem": modem_group_s,
    "modem_chflt": modem_chflt_group_s,
    "pa": pa_group_s,
    "synth": synth_group_s,
    "match": match_group_s,
    "freq_control": freq_control_group_s,
    "rx_hop": rx_hop_group_s
}
