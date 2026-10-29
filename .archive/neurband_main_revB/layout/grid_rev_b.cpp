// Three signal layers, one uninterrupted ground plane. Coordinates are grid cells.
#include <vector>
#include <queue>
#include <cmath>
#include <algorithm>
#include <cstdint>
#include <limits>
struct Q {float f,g; int n; bool operator<(const Q&o)const{return f>o.f;}};
extern "C" int route(const uint8_t* blocked,const uint8_t* viaok,int w,int h,int layers,const int* starts,int ns,const int* goals,int ng,int* result,int maxout,int viapen,int maxnodes){
 const int wh=w*h,N=wh*layers;std::vector<float>d(N,std::numeric_limits<float>::infinity());std::vector<int> prev(N,-1);std::vector<uint8_t> target(N,0);std::vector<int> gx,gy,gz;
 for(int k=0;k<ng;k++){int n=goals[k];target[n]=1;gx.push_back(n%w);gy.push_back(n/ w%h);gz.push_back(n/wh);}
 auto heuristic=[&](int n){int x=n%w,y=n/w%h,z=n/wh;float a=1e20f;for(int k=0;k<ng;k++){int dx=abs(x-gx[k]),dy=abs(y-gy[k]);float v=std::max(dx,dy)+0.41421356f*std::min(dx,dy)+(z!=gz[k]?viapen:0);a=std::min(a,v);}return a;};
 std::priority_queue<Q>q;for(int k=0;k<ns;k++){int n=starts[k];d[n]=0;q.push({heuristic(n),0,n});}
 const int dx[8]={1,-1,0,0,1,1,-1,-1},dy[8]={0,0,1,-1,1,-1,1,-1};int count=0,end=-1;
 while(!q.empty()&&count++<maxnodes){auto a=q.top();q.pop();if(a.g>d[a.n])continue;int n=a.n;if(target[n]){end=n;break;}int x=n%w,y=n/w%h,z=n/wh;
 for(int k=0;k<8;k++){int xx=x+dx[k],yy=y+dy[k];if(xx<0||xx>=w||yy<0||yy>=h)continue;int m=z*wh+yy*w+xx;if(blocked[m])continue;if(k>=4&&(blocked[z*wh+y*w+xx]||blocked[z*wh+yy*w+x]))continue;float g=a.g+(k<4?1:1.41421356f);if(g<d[m]){d[m]=g;prev[m]=n;q.push({g+heuristic(m),g,m});}}
 if(viaok[y*w+x])for(int zz=0;zz<layers;zz++){if(zz==z)continue;int m=zz*wh+y*w+x;if(blocked[m])continue;float g=a.g+viapen;if(g<d[m]){d[m]=g;prev[m]=n;q.push({g+heuristic(m),g,m});}}
 }
 if(end<0)return -count;std::vector<int>path;for(int n=end;n>=0;n=prev[n]){path.push_back(n);if(path.size()>(size_t)maxout)return 0;}std::reverse(path.begin(),path.end());for(size_t k=0;k<path.size();k++)result[k]=path[k];return path.size();
}
extern "C" int flood(const uint8_t* b,const uint8_t* v,int w,int h,int start,uint8_t* seen,int* stats){
 std::vector<int> q;q.push_back(start);seen[start]=1;int nv=0,minx=w,maxx=0,miny=h,maxy=0;
 for(size_t k=0;k<q.size();k++){int n=q[k],x=n%w,y=n/w;nv+=v[n]!=0;minx=std::min(minx,x);maxx=std::max(maxx,x);miny=std::min(miny,y);maxy=std::max(maxy,y);
  for(int d=0;d<4;d++){int xx=x+(d==0)-(d==1),yy=y+(d==2)-(d==3);if(xx<0||yy<0||xx>=w||yy>=h)continue;int m=yy*w+xx;if(!b[m]&&!seen[m]){seen[m]=1;q.push_back(m);}}
 }
 stats[0]=q.size();stats[1]=nv;stats[2]=minx;stats[3]=miny;stats[4]=maxx;stats[5]=maxy;return q.size();
}
