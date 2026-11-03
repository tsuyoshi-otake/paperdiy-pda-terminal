#include "vt.h"
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <sstream>
using namespace term;
static std::string u8(uint32_t cp){ std::string s; if(cp<0x80) s+=(char)cp; else if(cp<0x800){s+=(char)(0xC0|(cp>>6)); s+=(char)(0x80|(cp&0x3F));} else if(cp<0x10000){s+=(char)(0xE0|(cp>>12)); s+=(char)(0x80|((cp>>6)&0x3F)); s+=(char)(0x80|(cp&0x3F));} else {s+=(char)(0xF0|(cp>>18)); s+=(char)(0x80|((cp>>12)&0x3F)); s+=(char)(0x80|((cp>>6)&0x3F)); s+=(char)(0x80|(cp&0x3F));} return s; }
int main(int argc,char**argv){ std::ifstream f(argv[1],std::ios::binary); std::stringstream ss; ss<<f.rdbuf(); std::string d=ss.str();
 Vt t(80,24); t.on_reply=[](const char*,size_t){}; size_t pos=0;
 for(int a=2;a<=argc;a++){ size_t end = a<argc? std::min((size_t)atol(argv[a]), d.size()) : d.size(); t.feed(d.data()+pos, end-pos); pos=end;
   printf("\x01SNAP%zu cursor %d %d\n", end, t.cursorX(), t.cursorY());
   for(int y=0;y<24;y++){ std::string line; for(int x=0;x<80;x++){ const Cell&c=t.cell(x,y); if(c.width==0) continue; line+=u8(c.cp);} while(!line.empty()&&line.back()==' ') line.pop_back(); printf("%s\n", line.c_str()); } }
}
