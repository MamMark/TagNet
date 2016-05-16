#
#
from __future__ import print_function

from twisted.python.constants import Names, NamedConstant

from machinist import TransitionTable, MethodSuffixOutputer, constructFiniteStateMachine

from si446xFSM import Events, Actions, States, table
from si446xact import Si446xActionProcs

class Action_code(object):
    def __init__(self, dev_num):
        self.actions = Si446xActionProcs(dev_num)

    def output_A_CLEAR_SYNC(self, ev):
        print("clear sync")
    def output_A_CONFIG(self, ev):
        print("config")
        self.actions.config()
    def output_A_NOP (self, ev):
        print("nop")
    def output_A_PWR_DN(self, ev):
        print("power down")
    def output_A_PWR_UP(self, ev):
        print("power up")
        self.actions.pwr_up()
    def output_A_READY (self, ev):
        print("ready")
    def output_A_RX_CMP(self, ev):
        print("rx complete")
    def output_A_RX_CNT_CRC(self, ev):
        print("rx count crc error")
    def output_A_RX_DRAIN_FF(self, ev):
        print("drain rx fifo")
    def output_A_RX_START(self, ev):
        print("rx start")
    def output_A_RX_TIMEOUT(self, ev):
        print("rx timeout")
    def output_A_STANDBY(self, ev):
        print("standby")
    def output_A_TX_CMP(self, ev):
        print("tx complete")
    def output_A_TX_FILL_FF(self, ev):
        print("tx fill fifo")
    def output_A_TX_START(self, ev):
        print("tx start")
    def output_A_TX_TIMEOUT(self, ev):
        print("tx timeout")
    def output_A_UNSHUT(self, ev):
        print("unshutdown")
        self.actions.unshut()
        


si446xDriver = constructFiniteStateMachine(
    inputs=Events,
    outputs=Actions,
    states=States,
    table=table,
    initial=States.S_SDN,
    richInputs=[],
    inputContext={},
    world=MethodSuffixOutputer(Action_code(0)),
)

def cycle():
    si446xDriver.receive(Events.E_TURNON)
    si446xDriver.receive(Events.E_WAIT_DONE)
    si446xDriver.receive(Events.E_WAIT_DONE)
    si446xDriver.receive(Events.E_CONFIG_DONE)
    si446xDriver.receive(Events.E_TURNOFF)
#    si446xDriver.receive(Events.E_WAIT_DONE)


if __name__ == '__main__':
    cycle()
