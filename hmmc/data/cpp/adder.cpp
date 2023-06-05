using namespace std;
#include <stdlib.h>
#include "Vtop.h"
#include "verilated.h"
#include <verilated_vcd_c.h>


int main(int argc, char **argv) {
    // Using unique_ptr to automatically destroy VerilatedContext instance
    const std::unique_ptr<VerilatedContext> contextp{new VerilatedContext};

    // Create logs/ directory in case we have traces to put under it
    Verilated::mkdir("logs");

    // Initialize Verilators variables
    Verilated::commandArgs(argc, argv);

    // Create an instance of our module under test
    const std::unique_ptr<Vtop> top{new Vtop{contextp.get(), "top"}};

    // Verilator must compute traced signals
    contextp->traceEverOn(true);
    #if VM_TRACE_VCD
    VerilatedVcdC* tfp = new VerilatedVcdC;
    top->trace(tfp, 99);  // Trace 99 levels of hierarchy (or see below)
    tfp->open("logs/test_utils_verilator.vcd");
    #endif

    // initial setup
    top->a = 0xdeadbeef;
    top->b = 0x8badf00d;

    // Tick the clock until we are done
    for(int i=0; i<=1; i++)
    {
        // do a clock tick
        contextp->timeInc(5);
        top->sys_clk = 0;
        top->eval(); // Evaluate model
        #if VM_TRACE_VCD
        tfp->dump(contextp->time());
        #endif
        contextp->timeInc(5);
        top->sys_clk = 1;
        top->eval(); // Evaluate model
        #if VM_TRACE_VCD
        tfp->dump(contextp->time());
        #endif
    }

    // Final model cleanup
    top->final();
    #if VM_TRACE_VCD
    tfp->close();
    #endif

    return  top->c == (0xFFFFFFFF & (0xdeadbeef + 0x8badf00d)) ? 0 : 1;
}
