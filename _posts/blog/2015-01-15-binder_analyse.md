---
layout: post
title: 分析Binder运行过程:
description: This is android Project. 
category: blog
---
所有代码研究基于android4.2.2_R1 

# 从MediaService开始分析
## MediaService分析
framework\base\Media\MediaServer\Main_mediaserver.cpp

	{% highlight java linenos %} 
	int main(int argc, char** argv)
{

//获得一个ProcessState实例
    sp<ProcessState> proc(ProcessState::self());

	//得到一个ServiceManager对象
    sp<IServiceManager> sm = defaultServiceManager();
    ALOGI("ServiceManager: %p", sm.get());
    AudioFlinger::instantiate();
    MediaPlayerService::instantiate();//初始化MediaPlayerService服务
    CameraService::instantiate();
    AudioPolicyService::instantiate();
    ProcessState::self()->startThreadPool(); 
    IPCThreadState::self()->joinThreadPool();
}

	{% endhighlight %}
## ProcessState的
主要关注的是ProcessState,第一行就调用的是ProcessState::self().

	{% highlight java linenos %} 
	sp<ProcessState> ProcessState::self()
{
    Mutex::Autolock _l(gProcessMutex);
    if (gProcess != NULL) {
        return gProcess;
    }
    gProcess = new ProcessState;
    return gProcess;
}
	{% endhighlight %}
ProcessState的构造函数

	{% highlight java linenos %} 
	ProcessState::ProcessState()
    : mDriverFD(open_driver())
    , mVMStart(MAP_FAILED)
    , mManagesContexts(false)
    , mBinderContextCheckFunc(NULL)
    , mBinderContextUserData(NULL)
    , mThreadPoolStarted(false)
    , mThreadPoolSeq(1)
{
    if (mDriverFD >= 0) {
        // XXX Ideally, there should be a specific define for whether we
        // have mmap (or whether we could possibly have the kernel module
        // availabla).
#if !defined(HAVE_WIN32_IPC)
        // mmap the binder, providing a chunk of virtual address space to receive transactions.
        mVMStart = mmap(0, BINDER_VM_SIZE, PROT_READ, MAP_PRIVATE | MAP_NORESERVE, mDriverFD, 0);
        if (mVMStart == MAP_FAILED) {
            // *sigh*
            ALOGE("Using /dev/binder failed: unable to mmap transaction memory.\n");
            close(mDriverFD);
            mDriverFD = -1;
        }
#else
        mDriverFD = -1;
#endif
    }

    LOG_ALWAYS_FATAL_IF(mDriverFD < 0, "Binder driver could not be opened.  Terminating.");
}


	{% endhighlight %}
这里已经调用open_driver()，open_driver，就是打开/dev/binder这个设备，这个是android在内核中搞的一个专门用于完成
进程间通讯而设置的一个虚拟的设备。BTW，说白了就是内核的提供的一个机制，这个和我们用socket加NET_LINK方式和内核通讯是一个道理。

	{% highlight java linenos %} 
	static int open_driver()
{
    int fd = open("/dev/binder", O_RDWR);
    if (fd >= 0) {
        fcntl(fd, F_SETFD, FD_CLOEXEC);
        int vers;
        status_t result = ioctl(fd, BINDER_VERSION, &vers);
        if (result == -1) {
            ALOGE("Binder ioctl to obtain version failed: %s", strerror(errno));
            close(fd);
            fd = -1;
        }
        if (result != 0 || vers != BINDER_CURRENT_PROTOCOL_VERSION) {
            ALOGE("Binder driver protocol does not match user space protocol!");
            close(fd);
            fd = -1;
        }
        size_t maxThreads = 15;
        result = ioctl(fd, BINDER_SET_MAX_THREADS, &maxThreads);
        if (result == -1) {
            ALOGE("Binder ioctl to set max threads failed: %s", strerror(errno));
        }
    } else {
        ALOGW("Opening '/dev/binder' failed: %s\n", strerror(errno));
    }
    return fd;
}
	{% endhighlight %}i
1. 打开/dev/binder设备，这样的话就相当于和内核binder机制有了交互的通道
2. 映射fd到内存，设备的fd传进去后，估计这块内存是和binder设备共享的

## defaultServiceManager分析
defaultServiceManager位置在framework\base\libs\binder\IServiceManager.cpp中

	{% highlight java linenos %} 
	sp<IServiceManager> defaultServiceManager()
{
    if (gDefaultServiceManager != NULL) return gDefaultServiceManager;
    
    {
        AutoMutex _l(gDefaultServiceManagerLock);
        if (gDefaultServiceManager == NULL) {
			//真正的gDefaultServiceManager是在这里创建的喔
            gDefaultServiceManager = interface_cast<IServiceManager>(
                ProcessState::self()->getContextObject(NULL));
        }
    }
    
    return gDefaultServiceManager;
}
	{% endhighlight %}

分析代码就可以理解出来，其实调用是这样的

	{% highlight java linenos %} 
	gDefaultServiceManager = interface_cast<IServiceManager>(new BpBinder(0));
	{% endhighlight %}

interface_cast函数
\frameworks\native\include\binder\IInterface.h：


	{% highlight java linenos %} 
template<typename INTERFACE>
inline sp<INTERFACE> interface_cast(const sp<IBinder>& obj)
{
    return INTERFACE::asInterface(obj);
}
	{% endhighlight %}

结合前面就是：
{% highlight java linenos %} 
inline sp<IServiceManager> interface_cast(const sp<IBinder>& obj)
{
    return IServiceManager::asInterface(obj);
}
{% endhighlight %}
所以需要到IServiceManager里面去看看是如何实现的:	
\frameworks\native\include\binder\IServiceManager.h：
{% highlight java linenos %} 
class IServiceManager : public IInterface
{
public:
    DECLARE_META_INTERFACE(ServiceManager);
    /**
     * Retrieve an existing service, blocking for a few seconds
     * if it doesn't yet exist.
     */
    virtual sp<IBinder>         getService( const String16& name) const = 0;

    /**
     * Retrieve an existing service, non-blocking.
     */
    virtual sp<IBinder>         checkService( const String16& name) const = 0;

    /**
     * Register a service.
     */
    virtual status_t            addService( const String16& name,
                                            const sp<IBinder>& service,
                                            bool allowIsolated = false) = 0;

    /**
     * Return list of all existing services.
     */
    virtual Vector<String16>    listServices() = 0;

    enum {
        GET_SERVICE_TRANSACTION = IBinder::FIRST_CALL_TRANSACTION,
        CHECK_SERVICE_TRANSACTION,
        ADD_SERVICE_TRANSACTION,
        LIST_SERVICES_TRANSACTION,
    };
};


//DECLARE_META_INTERFACE 声明: IInterface.h

#define DECLARE_META_INTERFACE(INTERFACE)                               \
    static const android::String16 descriptor;                          \
    static android::sp<I##INTERFACE> asInterface(                       \
            const android::sp<android::IBinder>& obj);                  \
    virtual const android::String16& getInterfaceDescriptor() const;    \
    I##INTERFACE();                                                     \
    virtual ~I##INTERFACE();                                            \


{% endhighlight %}
替换成IServiceManager：

{% highlight java linenos %} 
//实现时传入：android.os.IServiceManager
static const android::String16 descriptor; 
static android::sp<IServiceManager> asInterface( 
const android::sp<android::IBinder>& obj); 
virtual const android::String16& getInterfaceDescriptor() const; 
//构造析构函数
IServiceManager(); 
virtual ~IServiceManager(); 

{% endhighlight %}
实现\frameworks\native\include\binder\IServiceManager.cpp：

{% highlight java linenos %} 
IMPLEMENT_META_INTERFACE(ServiceManager, "android.os.IServiceManager");

{% endhighlight %}
IMPLEMENT_META_INTERFACE实现：IInterface.h

{% highlight java linenos %} 
#define IMPLEMENT_META_INTERFACE(INTERFACE, NAME)                       \
    const android::String16 I##INTERFACE::descriptor(NAME);             \
    const android::String16&                                            \
            I##INTERFACE::getInterfaceDescriptor() const {              \
        return I##INTERFACE::descriptor;                                \
    }                                                                   \
    android::sp<I##INTERFACE> I##INTERFACE::asInterface(                \
            const android::sp<android::IBinder>& obj)                   \
    {                                                                   \
        android::sp<I##INTERFACE> intr;                                 \
        if (obj != NULL) {                                              \
            intr = static_cast<I##INTERFACE*>(                          \
                obj->queryLocalInterface(                               \
                        I##INTERFACE::descriptor).get());               \
            if (intr == NULL) {                                         \
                intr = new Bp##INTERFACE(obj);                          \
            }                                                           \
        }                                                               \
        return intr;                                                    \
    }                                                                   \
    I##INTERFACE::I##INTERFACE() { }                                    \
    I##INTERFACE::~I##INTERFACE() { }                                   \

{% endhighlight %}
替换成IServiceManager:

{% highlight java linenos %} 
android::sp<IServiceManager> IServiceManager::asInterface(                
            const android::sp<android::IBinder>& obj)                   
{   
        //obj BpBinder实例                                                                
        android::sp<IServiceManager> intr;                                
        if (obj != NULL) {
            //返回NULL                                        
            intr = static_cast<IServiceManager*>(                          
                obj->queryLocalInterface(                               
                        IServiceManager::descriptor).get());              
            if (intr == NULL) {                                         
                intr = new BpServiceManager(obj);                          
            }                                                           
        }                                                               
        return intr;                                                    
}
{% endhighlight %}

可以看出这个gDefaultServiceManager的实例其实是

{% highlight java linenos %} 
	BpServiceManager：new BpServiceManager（new BpBinder（0））；
{% endhighlight %}
##BpServiceManager 和BpInterface

\frameworks\native\libs\binder\ IServiceManager.cpp：BpServiceManager

{% highlight java linenos %} 
class BpServiceManager : public BpInterface<IServiceManager>
{
public:
      //impl就是 new BpBinder（0）
    BpServiceManager(const sp<IBinder>& impl)
        : BpInterface<IServiceManager>(impl)
    {
    }

    virtual sp<IBinder> checkService(const String16& name) const
    {
        ……
        remote()->transact(CHECK_SERVICE_TRANSACTION, data, &reply);
    }

    virtual status_t addService(const String16& name, const sp<IBinder>& service,
            bool allowIsolated)
    {
        ……
        remote()->transact(ADD_SERVICE_TRANSACTION, data, &reply);
    }
}
{% endhighlight %}
\frameworks\native\include\binder\ IInterface.h：模板类BpInterface

{% highlight java linenos %} 
template<typename INTERFACE>
class BpInterface : public INTERFACE, public BpRefBase
{
public:
                                BpInterface(const sp<IBinder>& remote);

protected:
    virtual IBinder*            onAsBinder();
};

{% endhighlight %}
BpInterface的构造函数是空的就不用看了，直接看BpRefBase：

{% highlight java linenos %} 
BpRefBase::BpRefBase(const sp<IBinder>& o)
    : mRemote(o.get()), mRefs(NULL), mState(0)
{
    extendObjectLifetime(OBJECT_LIFETIME_WEAK);
	// IBinder mRemote 指向 o.get() ：new BpBinder（0）
    if (mRemote) {
        mRemote->incStrong(this);           // Removed on first IncStrong().
        mRefs = mRemote->createWeak(this);  // Held for our entire lifetime.
    }
}

{% endhighlight %}
gDefaultServiceManager = interface_cast<IServiceManager>(BpBinder(0))；
实际为：
　　gDefaultServiceManager = new BpServiceManager（new BpBinder（0））；
Bn代表Binder Native	Bp代表Binder Proxy
BpServiceManager代理的BpBinder实例 BpBinder代理的handle（0）

在Media Process 的main函数中通过：

sp<IServiceManager> sm = defaultServiceManager();
　　我们得到了sm：是BpServiceManager对象

在回顾MediaPlayerService做了哪些:
{% highlight java linenos %} 
int main(int argc, char** argv)
{
    sp<ProcessState> proc(ProcessState::self());
    sp<IServiceManager> sm = defaultServiceManager();
    ALOGI("ServiceManager: %p", sm.get());
    AudioFlinger::instantiate();
    MediaPlayerService::instantiate();
    CameraService::instantiate();
    AudioPolicyService::instantiate();
    ProcessState::self()->startThreadPool();
    IPCThreadState::self()->joinThreadPool();
}
{% endhighlight %}
MediaPlayerService初始化过程:

{% highlight java linenos %} 
void MediaPlayerService::instantiate() {
    defaultServiceManager()->addService(
            String16("media.player"), new MediaPlayerService());
}
{% endhighlight %}
看BpServiceManager的addService方法

{% highlight java linenos %} 
virtual status_t addService(const String16& name, const sp<IBinder>& service,
            bool allowIsolated)
    {
        Parcel data, reply;
		// Write RPC headers 写入Interface名字 得到“android.os.IServiceManager”
        data.writeInterfaceToken(IServiceManager::getInterfaceDescriptor());
//写入Service名字 “media.player”
        data.writeString16(name);
//写入服务
        data.writeStrongBinder(service);
        data.writeInt32(allowIsolated ? 1 : 0);
// remote()返回BpBinder对象
        status_t err = remote()->transact(ADD_SERVICE_TRANSACTION, data, &reply);
        return err == NO_ERROR ? reply.readExceptionCode() : err;
    }
{% endhighlight %}

调用的是BpBinder的transact:
{% highlight java linenos %} 
status_t BpBinder::transact(
    uint32_t code, const Parcel& data, Parcel* reply, uint32_t flags)
{
    // Once a binder has died, it will never come back to life.
    if (mAlive) {
        status_t status = IPCThreadState::self()->transact(
            mHandle, code, data, reply, flags);
        if (status == DEAD_OBJECT) mAlive = 0;
        return status;
    }

    return DEAD_OBJECT;
}
{% endhighlight %}

## IPCThreadState中写入数据到Binder设备过程

{% highlight java linenos %} 
status_t IPCThreadState::transact(int32_t handle,
                                  uint32_t code, const Parcel& data,
                                  Parcel* reply, uint32_t flags)
{
    status_t err = data.errorCheck();

    flags |= TF_ACCEPT_FDS;

  	......    
      
    if (err != NO_ERROR) {
        if (reply) reply->setError(err);
        return (mLastError = err);
    }
    
    if ((flags & TF_ONE_WAY) == 0) {
        #if 0
        if (code == 4) { // relayout
            ALOGI(">>>>>> CALLING transaction 4");
        } else {
            ALOGI(">>>>>> CALLING transaction %d", code);
        }
        #endif
        if (reply) {
            err = waitForResponse(reply);
        } else {
            Parcel fakeReply;
            err = waitForResponse(&fakeReply);
        }
        #if 0
        if (code == 4) { // relayout
            ALOGI("<<<<<< RETURNING transaction 4");
        } else {
            ALOGI("<<<<<< RETURNING transaction %d", code);
        }
        #endif
       } else {
        err = waitForResponse(NULL, NULL);
    }
    
    return err;
}

status_t IPCThreadState::waitForResponse(Parcel *reply, status_t *acquireResult)
{
    while (1) {
        //将数据写入到Binder设备中
        talkWithDriver();
        ……
    }
    return err;
}
status_t IPCThreadState::talkWithDriver(bool doReceive)
{
    //将数据封装成binder_write_read结构
    binder_write_read bwr;

    do {
        //将数据写入到所打开的Binder设备中
        ioctl(mProcess->mDriverFD, BINDER_WRITE_READ, &bwr)
        ……
    
    } while (err == -EINTR);
    return NO_ERROR;
}

{% endhighlight %}

将MediaPlayerService加入到ServiceManager中，
这里就通过BpServiceManager的AddService将数据写入到Binder设备传递给ServiceManager。
## Media Process消息循环

{% highlight java linenos %} 
int main(int argc, char** argv)
{
    //启动进程的线程池    
    ProcessState::self()->startThreadPool();     //走到了这里

    //执行线程消息循环
    IPCThreadState::self()->joinThreadPool();
}
{% endhighlight %}
ProcessState::self()->startThreadPool(); -----> 创建工作者线程:
startThreadPool：\frameworks\native\libs\binder\ ProcessState.cpp：

{% highlight java linenos %} 
void ProcessState::spawnPooledThread(bool isMain)
{
    if (mThreadPoolStarted) {
        int32_t s = android_atomic_add(1, &mThreadPoolSeq);
        char buf[16];
        snprintf(buf, sizeof(buf), "Binder_%X", s);
        ALOGV("Spawning new pooled thread, name=%s\n", buf);
//创建PoolThread对象 并run ，非线程
        sp<Thread> t = new PoolThread(isMain);
        t->run(buf);
    }
}
{% endhighlight %}
PoolThread继承Thread
执行Thread的run函数 
位于utils/Threads.cpp

{% highlight java linenos %} 
status_t Thread::run(const char* name, int32_t priority, size_t stack)
{
    //创建线程mThread _threadLoop
    bool res;
    res = createThreadEtc(_threadLoop,
    this, name, priority, stack, &mThread);

    return NO_ERROR;
}
{% endhighlight %}
现在有两个线程：主线程和mThread线程
mThread线程执行：_threadLoop

{% highlight java linenos %} 
int Thread::_threadLoop(void* user)
{
    Thread* const self = static_cast<Thread*>(user);
    do {
        //调用子类的threadLoop
        result = self->threadLoop();
        ……
    } while(strong != 0);
    return 0;
}

class PoolThread : public Thread
{
protected:
    virtual bool threadLoop()
    {
        IPCThreadState::self()->joinThreadPool(mIsMain);
        return false;
    }
};
{% endhighlight %}
## 进程间通信消息循环过程

消息循环:

{% highlight java linenos %} 
void IPCThreadState::joinThreadPool(bool isMain)
{
    mOut.writeInt32(isMain ? BC_ENTER_LOOPER : BC_REGISTER_LOOPER);
    status_t result;    
    //消息循环
    do {
        int32_t cmd;
        //从binder设备中读取命令
        result = talkWithDriver();
        if (result >= NO_ERROR) {
            cmd = mIn.readInt32();
            //执行命令
            result = executeCommand(cmd);
        }
           ……
    } while (result != -ECONNREFUSED && result != -EBADF);
    
    mOut.writeInt32(BC_EXIT_LOOPER);
    talkWithDriver(false);
}
{% endhighlight %}
命令执行：
{% highlight java linenos %} 
status_t IPCThreadState::executeCommand(int32_t cmd)
{
    BBinder* obj;
    RefBase::weakref_type* refs;
    switch (cmd) {
    case BR_DECREFS:
        break;
    case BR_ATTEMPT_ACQUIRE:
        break;
case BR_TRANSACTION:
　　binder_transaction_data tr;
    result = mIn.read(&tr, sizeof(tr));
      if (tr.target.ptr) {
        //将目标对象转化成BBinder
        sp<BBinder> b((BBinder*)tr.cookie);
        //调用BBinder的transact 函数
       const status_t error = b->transact(tr.code, buffer, &reply, tr.flags);
      }
        break;
    ……
    default:
    }
    return result;
}

{% endhighlight %}
binder_transaction_data.cookie：target object cookie目标对象，这个target object是指那个呢？

在Media Process里面有几个Service：AudioFlinger、MediaPlayerService、CameraService等。

这个目标是这其中Service中的一个，假设目标对象为为MediaPlayerService，那为何要转化成BBinder呢？

## Service对命令的处理
线程从binder接收到消息命令，将命令传递给Service处理。将目标对象转化成BBinder，然后调度此命令；
命令从远端传递到本地端进行处理，每个Service都对应BnXXX对象来处理远端BpXXX传来的命令。
　　sp<BBinder> b((BBinder*)tr.cookie);
　　const status_t error = b->transact(tr.code, buffer, &reply, tr.flags);
　　这里b代表某个Service：假设为MediaPlayerService；弄清楚执行过程，要弄清楚类继承关系。

本地端BnMediaPlayerService消息处理过程：真正的对象是MediaPlayerService实例。
从BBinder ->transact开始传递：

{% highlight java linenos %} 
status_t BBinder::transact(
    uint32_t code, const Parcel& data, Parcel* reply, uint32_t flags)
{
    data.setDataPosition(0);

    status_t err = NO_ERROR;
    switch (code) {
        case PING_TRANSACTION:
            reply->writeInt32(pingBinder());
            break;
        default:
		//onTransact是个virtual函数 派生类BnMediaPlayerService重写
            err = onTransact(code, data, reply, flags);
            break;
    }

    if (reply != NULL) {
        reply->setDataPosition(0);
    }

    return err;
}
{% endhighlight %}
调用的是onTransact(code, data, reply, flags); BBinder的onTransact是虚函数，被子类BnMediaPlayerService复写:

{% highlight java linenos %} 


{% endhighlight %}
{% highlight java linenos %} {% endhighlight %}




{% highlight java linenos %} {% endhighlight %}



{% highlight java linenos %} {% endhighlight %}



这里调用的ProcessState的getContextObject;

	{% highlight java linenos %} 
	sp<IBinder> ProcessState::getContextObject(const sp<IBinder>& caller)
{
    return getStrongProxyForHandle(0);
}

	sp<IBinder> ProcessState::getStrongProxyForHandle(int32_t handle)
{
    sp<IBinder> result;

    AutoMutex _l(mLock);

    handle_entry* e = lookupHandleLocked(handle);

    if (e != NULL) {
        // We need to create a new BpBinder if there isn't currently one, OR we
        // are unable to acquire a weak reference on this current one.  See comment
        // in getWeakProxyForHandle() for more info about this.
        IBinder* b = e->binder;
        if (b == NULL || !e->refs->attemptIncWeak(this)) {
            b = new BpBinder(handle); 
            e->binder = b;
            if (b) e->refs = b->getWeakRefs();
            result = b;
        } else {
            // This little bit of nastyness is to allow us to add a primary
            // reference to the remote proxy when this team doesn't have one
            // but another team is sending the handle to us.
            result.force_set(b);
            e->refs->decWeak(this);
        }
    }

    return result;
}
	{% endhighlight %}






{% highlight java linenos %} {% endhighlight %}
{% highlight java linenos %} {% endhighlight %}


{% highlight java linenos %} {% endhighlight %}

在看看BpBinder：
## BpBinder

	{% highlight java linenos %} 
BpBinder::BpBinder(int32_t handle)
    : mHandle(handle)
    , mAlive(1)
    , mObitsSent(0)
    , mObituaries(NULL)
{
    ALOGV("Creating BpBinder %p handle %d\n", this, mHandle);

    extendObjectLifetime(OBJECT_LIFETIME_WEAK);
    IPCThreadState::self()->incWeakHandle(handle);//FT，竟然到IPCThreadState::self()
}
	{% endhighlight %}
这里一块说说吧，IPCThreadState::self估计怎么着又是一个singleton吧？

//该文件位置在framework\base\libs\binder\IPCThreadState.cpp
	{% highlight java linenos %} 
	IPCThreadState* IPCThreadState::self()
{
    if (gHaveTLS) {
restart:
        const pthread_key_t k = gTLS;
//TLS是Thread Local Storage的意思，不懂得自己去google下它的作用吧。这里只需要

//知道这种空间每个线程有一个，而且线程间不共享这些空间，好处是？我就不用去搞什么

//同步了。在这个线程，我就用这个线程的东西，反正别的线程获取不到其他线程TLS中的数据。===》这句话有漏洞，钻牛角尖的明白大概意思就可以了。

//从线程本地存储空间中获得保存在其中的IPCThreadState对象

//这段代码写法很晦涩，看见没，只有pthread_getspecific,那么肯定有地方调用

// pthread_setspecific
        IPCThreadState* st = (IPCThreadState*)pthread_getspecific(k);
        if (st) return st;
        return new IPCThreadState;
    }
    
    if (gShutdown) return NULL;
    
    pthread_mutex_lock(&gTLSMutex);
    if (!gHaveTLS) {
        if (pthread_key_create(&gTLS, threadDestructor) != 0) {
            pthread_mutex_unlock(&gTLSMutex);
            return NULL;
        }
        gHaveTLS = true;
    }
    pthread_mutex_unlock(&gTLSMutex);
    goto restart;
}

	{% endhighlight %}
构造函数:


	{% highlight java linenos %} 



	{% endhighlight %}
	{% highlight java linenos %} {% endhighlight %}
	{% highlight java linenos %} {% endhighlight %}


	{% highlight java linenos %} {% endhighlight %}
	{% highlight java linenos %} {% endhighlight %}


	{% highlight java linenos %} {% endhighlight %}





<ul>
	<li>jekyll打开本地服务jekyll serve</li>
	<li>关于jekyll的 Address already in use - bind(2):</br>
		先采用lsof -wni tcp:4000 或者使用 ps aux |grep "jek"</br>
		再采用kill -9 PID命令
		</li>
	
</ul>

	
![Alt text]( /images/android/androidL_1.png "Optional title")


- ​http://developer.android.com/preview/api-overview.html
- ​http://developer.android.com/preview/api-overview.html
- ​http://developer.android.com/preview/api-overview.html
- ​http://developer.android.com/preview/api-overview.html	

	{% highlight java linenos %} {% endhighlight %}



### 结论

1.androd的底层实现是通过socket和共享内存的方式，这种写法也可以采用在我们自己的多进程通信上使用，值得学习
2.底层所有的event其实都是一样的，都是inputEvent，上层会根据source再分成keyEvent,MotionEvent等，用于不同的用处 
3.所有View的起点其实就是dispatchPointerEvent()，这个是分发事件的起点.


### 参考blog
http://www.cnblogs.com/-OYK/archive/2011/07/31/2122981.html
http://www.cnblogs.com/zhangxinyan/p/3487905.html
http://blog.csdn.net/yangwen123/article/details/9142521
http://blog.csdn.net/maxleng/article/details/5490770
http://www.cnblogs.com/innost/archive/2011/01/09/1931456.html
http://www.cnblogs.com/bastard/archive/2012/11/13/2766611.html
http://blog.csdn.net/a220315410/article/details/17761681

[本文基于android-2.3.3_r1代码研究]: http://daemon369.github.io/android/2014/09/11/android-dispatchTouchEvent/  "本文基于android-2.3.3_r1代码研究"
[Android事件分发机制完全解析，带你从源码的角度彻底理解]: http://blog.csdn.net/guolin_blog/article/details/9153747 "Android事件分发机制完全解析，带你从源码的角度彻底理解"
[android-inputevent传递过程]:http://blog.pickbox.me/2014/05/22/android-inputevent传递过程（app端）/ "android-inputevent传递过程"


[yangming]:  
