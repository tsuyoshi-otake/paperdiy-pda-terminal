#include "vt.h"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
using namespace term;
static std::string u8(uint32_t cp){ std::string s; if(cp<0x80) s+=(char)cp; else if(cp<0x800){s+=(char)(0xC0|(cp>>6)); s+=(char)(0x80|(cp&0x3F));} else if(cp<0x10000){s+=(char)(0xE0|(cp>>12)); s+=(char)(0x80|((cp>>6)&0x3F)); s+=(char)(0x80|(cp&0x3F));} else {s+=(char)(0xF0|(cp>>18)); s+=(char)(0x80|((cp>>12)&0x3F)); s+=(char)(0x80|((cp>>6)&0x3F)); s+=(char)(0x80|(cp&0x3F));} return s; }
static void dump(Vt& v, const char* title){ printf("=== %s (cursor %d,%d)\n", title, v.cursorX(), v.cursorY()); for(int y=0;y<v.rows();++y){ std::string line; for(int x=0;x<v.cols();++x){ const Cell&c=v.cell(x,y); if(c.width==0) continue; std::string g=u8(c.cp); if(c.attr&(kAttrInverse|kAttrDarkBg)) line+="\x1b[7m"+g+"\x1b[0m"; else line+=g; } while(!line.empty()&&line.back()==' ') line.pop_back(); printf("|%s\n", line.c_str()); } }
int main(int argc, char** argv){
  Vt v(40, 8);
  std::string replies; v.on_reply=[&](const char*d,size_t n){replies.append(d,n);};
  v.puts("hello\r\nworld\x1b[2;3H*\x1b[5;1Hline5\r\n\x1b[7minv\x1b[0m ok\r\n");
  v.puts("日本語テスト abc\r\n");
  v.puts("\x1b(0lqqk\x1b(B box\r\n");
  v.puts("\x1b[6n\x1b[c");
  dump(v,"basic");
  printf("replies: "); for(char c: replies) printf(c==27?"\\e":"%c", c); printf("\n");
  // wrap + wide at edge
  Vt w(10,4); w.puts("0123456789ABCDE\r\n012345678あい\r\n"); dump(w,"wrap");
  // scroll region + insert/delete lines
  Vt s(10,6); for(int i=0;i<6;i++) s.printf("L%d\r\n", i); s.puts("\x1b[2;4r\x1b[2;1H\x1b[L\x1b[r"); dump(s,"scroll region IL");
  // alt screen
  Vt a(10,4); a.puts("main1\r\nmain2"); a.puts("\x1b[?1049h\x1b[H\x1b[2Jalt!"); dump(a,"alt"); a.puts("\x1b[?1049l"); dump(a,"back");
  // resize
  Vt r(10,6); for(int i=0;i<6;i++) r.printf("R%d\r\n", i); r.resize(8,3); dump(r,"resized");
  if(argc>1){ std::ifstream f(argv[1], std::ios::binary); std::stringstream ss; ss<<f.rdbuf(); std::string d=ss.str(); Vt t(80,24); t.feed(d.data(), d.size()); dump(t, argv[1]); }
}
