using namespace std;
#include <stdlib.h>
#include "Vtop.h"
#include "verilated.h"
#include <verilated_vcd_c.h>
{includes}

{defines}

// default defines
#if !defined(VM_TRACE_VCD)
#define VM_TRACE_VCD 1
#endif

#if VM_TRACE_VCD
#define dump_vcd() tfp->dump(contextp->time())
#else
#define dump_vcd()
#endif

#if !defined(VM_TRACE_FILE)
#define VM_TRACE_FILE "logs/trace.vcd"
#endif

#define clock_tick(ctx, t) dump_vcd(); \
    ctx->timeInc(5); \
    t->sys_clk = 0; \
    t->eval(); \
    dump_vcd(); \
    ctx->timeInc(5); \
    t->sys_clk = 1; \
    t->eval(); \


int main(int argc, char **argv) {{
    // Using unique_ptr to automatically destroy VerilatedContext instance
    const std::unique_ptr<VerilatedContext> contextp{{new VerilatedContext}};

    // Create logs/ directory in case we have traces to put under it
    Verilated::mkdir("logs");

    // Initialize Verilators variables
    Verilated::commandArgs(argc, argv);

    // Create an instance of our module under test
    const std::unique_ptr<Vtop> top{{new Vtop{{contextp.get(), "top"}}}};

    // Verilator must compute traced signals
    contextp->traceEverOn(true);
    #if VM_TRACE_VCD
    VerilatedVcdC* tfp = new VerilatedVcdC;
    top->trace(tfp, 99);  // Trace 99 levels of hierarchy
    tfp->open(VM_TRACE_FILE);
    #endif

{main_code}

    // Final model cleanup
    clock_tick(contextp, top);
    top->final();
    #if VM_TRACE_VCD
    tfp->close();
    #endif

{return_code}
}}
