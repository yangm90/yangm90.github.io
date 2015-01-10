---
layout: post
title: 关于android的Activity是如何触摸事件框架简析(一) 
description: 关于android的Activity是如何触摸事件框架简析(一)
category: blog
---
最近做项目会修改导事件分发，所以对系统这部分代码进行了一定的研究，对android的框架的流的过程发出来供大家参考下.
所有代码研究基于android4.2.2_R1 

### Activity与windowMnager打交道的过程

	首先是我们如何开启一个ActivityThread的，在ActivityThread中我们做了什么:

在ActivityThread中会最先调用的是handleLaunchActivity-->handleResumeActivity;

	{% highlight java linenos %} 
	final void handleResumeActivity(IBinder token, boolean clearHide, boolean isForward,
            boolean reallyResume) {
		.......
		if (r.window == null && !a.mFinished && willBeVisible) {
                r.window = r.activity.getWindow();
                View decor = r.window.getDecorView();
                decor.setVisibility(View.INVISIBLE);
                ViewManager wm = a.getWindowManager();
                WindowManager.LayoutParams l = r.window.getAttributes();
                a.mDecor = decor;
                l.type = WindowManager.LayoutParams.TYPE_BASE_APPLICATION;
                l.softInputMode |= forwardBit;
                if (a.mVisibleFromClient) {
                    a.mWindowAdded = true;
                    wm.addView(decor, l);
                }
		......

	}
	{% endhighlight %}
核心代码就是上面的通过windowManager添加View,
这里的wm实体其实是_WindowMnagerGlobal_,查看addView:


	{% highlight java linenos %} 
	public void addView(View view, ViewGroup.LayoutParams params,
            Display display, Window parentWindow) {
		
		......
		ViewRootImpl root;
        View panelParentView = null;
		root = new ViewRootImpl(view.getContext(), display);
		view.setLayoutParams(wparams);
		......
		// do this last because it fires off messages to start doing things
        try {
            root.setView(view, wparams, panelParentView);
        } catch (RuntimeException e) {
            // BadTokenException or InvalidDisplayException, clean up.
            synchronized (mLock) {
                final int index = findViewLocked(view, false);
                if (index >= 0) {
                    removeViewLocked(index, true);
                }
            }
            throw e;
        }
}

	{% endhighlight %}
这里是new出了一个新的ViewRootImpl调用了setView方法:
ViewRootImpl.java

	{% highlight java linenos %} 
	/**
     * We have one child
     */
    public void setView(View view, WindowManager.LayoutParams attrs, View panelParentView) {
			......
			try {
                    mOrigWindowType = mWindowAttributes.type;
                    mAttachInfo.mRecomputeGlobalAttributes = true;
                    collectViewAttributes();
                    res = mWindowSession.addToDisplay(mWindow, mSeq, mWindowAttributes,
                            getHostVisibility(), mDisplay.getDisplayId(),
                            mAttachInfo.mContentInsets, mInputChannel);
                } catch (RemoteException e) {
                    mAdded = false;
                    mView = null;
                    mAttachInfo.mRootView = null;
                    mInputChannel = null;
                    mFallbackEventHandler.setView(null);
                    unscheduleTraversals();
                    setAccessibilityFocus(null, null);
                    throw new RuntimeException("Adding window failed", e);
                } finally {
                    if (restore) {
                        attrs.restore();
                    }
                }
			.......
			if (mInputChannel != null) {
                    if (mInputQueueCallback != null) {
                        mInputQueue = new InputQueue(mInputChannel);
                        mInputQueueCallback.onInputQueueCreated(mInputQueue);
                    } else {
                        mInputEventReceiver = new WindowInputEventReceiver(mInputChannel,
                                Looper.myLooper());
                    }
                }
}


	{% endhighlight %}

核心代码就是 mWindowSession.addToDisplay(),

	{% highlight java linenos %} 
	@Override
    public int addToDisplay(IWindow window, int seq, WindowManager.LayoutParams attrs,
            int viewVisibility, int displayId, Rect outContentInsets,
            InputChannel outInputChannel) {
        return mService.addWindow(this, window, seq, attrs, viewVisibility, displayId,
                outContentInsets, outInputChannel);
    }
	{% endhighlight %}
就是一个aidl调用，最终是调用的WindowManagerService的addWindow方法：

	{% highlight java linenos %} 
	    public int addWindow(Session session, IWindow client, int seq,
            WindowManager.LayoutParams attrs, int viewVisibility, int displayId,
            Rect outContentInsets, InputChannel outInputChannel) {

		......
		if (outInputChannel != null && (attrs.inputFeatures
                    & WindowManager.LayoutParams.INPUT_FEATURE_NO_INPUT_CHANNEL) == 0) {
                String name = win.makeInputChannelName();
                InputChannel[] inputChannels = InputChannel.openInputChannelPair(name);
                win.setInputChannel(inputChannels[0]);
                inputChannels[1].transferTo(outInputChannel);

                mInputManager.registerInputChannel(win.mInputChannel, win.mInputWindowHandle);
            }
		......
	}

	{% endhighlight %}
这里打开了一对inputChannel一个作为server端，一个作为client端，并且注册到inputManager里头.这个inputChannel其实就是pipe,我们看看他们是怎么生成的：
inputChannel.java
	{% highlight java linenos %} 
	/**
     * Creates a new input channel pair.  One channel should be provided to the input
     * dispatcher and the other to the application's input queue.
     * @param name The descriptive (non-unique) name of the channel pair.
     * @return A pair of input channels.  They are symmetric and indistinguishable.
     */
    public static InputChannel[] openInputChannelPair(String name) {
        if (name == null) {
            throw new IllegalArgumentException("name must not be null");
        }

        if (DEBUG) {
            Slog.d(TAG, "Opening input channel pair '" + name + "'");
        }
        return nativeOpenInputChannelPair(name);
    }
	{% endhighlight %}
natvie层对应代码：
android_view_inputchannel.cpp



	{% highlight java linenos %}
	static jobjectArray android_view_InputChannel_nativeOpenInputChannelPair(JNIEnv* env,
        jclass clazz, jstring nameObj) {
    const char* nameChars = env->GetStringUTFChars(nameObj, NULL);
    String8 name(nameChars);
    env->ReleaseStringUTFChars(nameObj, nameChars);

    sp<InputChannel> serverChannel;
    sp<InputChannel> clientChannel;
    status_t result = InputChannel::openInputChannelPair(name, serverChannel, clientChannel);

    if (result) {
        String8 message;
        message.appendFormat("Could not open input channel pair.  status=%d", result);
        jniThrowRuntimeException(env, message.string());
        return NULL;
    }

    jobjectArray channelPair = env->NewObjectArray(2, gInputChannelClassInfo.clazz, NULL);
    if (env->ExceptionCheck()) {
        return NULL;
    }

    jobject serverChannelObj = android_view_InputChannel_createInputChannel(env,
            new NativeInputChannel(serverChannel));
    if (env->ExceptionCheck()) {
        return NULL;
    }

    jobject clientChannelObj = android_view_InputChannel_createInputChannel(env,
            new NativeInputChannel(clientChannel));
    if (env->ExceptionCheck()) {
        return NULL;
    }

    env->SetObjectArrayElement(channelPair, 0, serverChannelObj);
    env->SetObjectArrayElement(channelPair, 1, clientChannelObj);
    return channelPair;
}	
 {% endhighlight %}
主要关注函数openInputChannelPair

	{% highlight java linenos %} 
	status_t InputChannel::openInputChannelPair(const String8& name,
        sp<InputChannel>& outServerChannel, sp<InputChannel>& outClientChannel) {
    int sockets[2];
    if (socketpair(AF_UNIX, SOCK_SEQPACKET, 0, sockets)) {
        status_t result = -errno;
        ALOGE("channel '%s' ~ Could not create socket pair.  errno=%d",
                name.string(), errno);
        outServerChannel.clear();
        outClientChannel.clear();
        return result;
    }

    int bufferSize = SOCKET_BUFFER_SIZE;
    setsockopt(sockets[0], SOL_SOCKET, SO_SNDBUF, &bufferSize, sizeof(bufferSize));
    setsockopt(sockets[0], SOL_SOCKET, SO_RCVBUF, &bufferSize, sizeof(bufferSize));
    setsockopt(sockets[1], SOL_SOCKET, SO_SNDBUF, &bufferSize, sizeof(bufferSize));
    setsockopt(sockets[1], SOL_SOCKET, SO_RCVBUF, &bufferSize, sizeof(bufferSize));

    String8 serverChannelName = name;
    serverChannelName.append(" (server)");
    outServerChannel = new InputChannel(serverChannelName, sockets[0]);

    String8 clientChannelName = name;
    clientChannelName.append(" (client)");
    outClientChannel = new InputChannel(clientChannelName, sockets[1]);
    return OK;
}
	 {% endhighlight %}

这里就可以发现双方是通过一个共享内存，socket的方式通信。这时候我们就已经初步的了解 Activity与windowManagerService是如何建立联系的.

### Activity接收事件过程
在ViewRootImpl中，我们会创建一个WindowInputEventReceiver，WindowInputEventReceiver的初始化会使用inputchannel和主线程的looper,继承于InputEventReceiver:


	{% highlight java linenos %} 
	**
     * Creates an input event receiver bound to the specified input channel.
     *
     * @param inputChannel The input channel.
     * @param looper The looper to use when invoking callbacks.
     */
    public InputEventReceiver(InputChannel inputChannel, Looper looper) {
        if (inputChannel == null) {
            throw new IllegalArgumentException("inputChannel must not be null");
        }
        if (looper == null) {
            throw new IllegalArgumentException("looper must not be null");
        }

        mInputChannel = inputChannel;
        mMessageQueue = looper.getQueue();
        mReceiverPtr = nativeInit(this, inputChannel, mMessageQueue);

        mCloseGuard.open("dispose");
    }

	{% endhighlight %}
会调用底层的nativeInit：
android_view_InputEventReceiver.cpp

	{% highlight java linenos %}  
	static jint nativeInit(JNIEnv* env, jclass clazz, jobject receiverObj,
        jobject inputChannelObj, jobject messageQueueObj) {
    sp<InputChannel> inputChannel = android_view_InputChannel_getInputChannel(env,
            inputChannelObj);
    if (inputChannel == NULL) {
        jniThrowRuntimeException(env, "InputChannel is not initialized.");
        return 0;
    }

    sp<MessageQueue> messageQueue = android_os_MessageQueue_getMessageQueue(env, messageQueueObj);
    if (messageQueue == NULL) {
        jniThrowRuntimeException(env, "MessageQueue is not initialized.");
        return 0;
    }

    sp<NativeInputEventReceiver> receiver = new NativeInputEventReceiver(env,
            receiverObj, inputChannel, messageQueue);
    status_t status = receiver->initialize();
    if (status) {
        String8 message;
        message.appendFormat("Failed to initialize input event receiver.  status=%d", status);
        jniThrowRuntimeException(env, message.string());
        return 0;
    }

    receiver->incStrong(gInputEventReceiverClassInfo.clazz); // retain a reference for the object
    return reinterpret_cast<jint>(receiver.get());
}
	{% endhighlight %}
这里其实是拿到上层的looper和上层的inputchannel去生成一个NativeInputEventReceiver，在看看NativeInputEventReceiver的作用:

	{% highlight java linenos %}
  	NativeInputEventReceiver::NativeInputEventReceiver(JNIEnv* env,
        jobject receiverObj, const sp<InputChannel>& inputChannel,
        const sp<MessageQueue>& messageQueue) :
        mReceiverObjGlobal(env->NewGlobalRef(receiverObj)),
        mInputConsumer(inputChannel), mMessageQueue(messageQueue),
        mBatchedInputEventPending(false) {
#if DEBUG_DISPATCH_CYCLE
    ALOGD("channel '%s' ~ Initializing input event receiver.", getInputChannelName());
#endif
}
	{% endhighlight %}

	{% highlight java linenos %}  
	status_t NativeInputEventReceiver::initialize() {
    int receiveFd = mInputConsumer.getChannel()->getFd();
    mMessageQueue->getLooper()->addFd(receiveFd, 0, ALOOPER_EVENT_INPUT, this, NULL);
    return OK;
}
	{% endhighlight %}
NativeInputEventReceiver实际上就是生成了一个mInputConsumer,并且调用initialize，将inputChannel的fd挂载到looper中去监听事件，回调函数为handleEvent：


	{% highlight java linenos %}  
	int NativeInputEventReceiver::handleEvent(int receiveFd, int events, void* data) {
    if (events & (ALOOPER_EVENT_ERROR | ALOOPER_EVENT_HANGUP)) {
        ALOGE("channel '%s' ~ Publisher closed input channel or an error occurred.  "
                "events=0x%x", getInputChannelName(), events);
        return 0; // remove the callback
    }

    if (!(events & ALOOPER_EVENT_INPUT)) {
        ALOGW("channel '%s' ~ Received spurious callback for unhandled poll event.  "
                "events=0x%x", getInputChannelName(), events);
        return 1;
    }

    JNIEnv* env = AndroidRuntime::getJNIEnv();
    status_t status = consumeEvents(env, false /*consumeBatches*/, -1);
    mMessageQueue->raiseAndClearException(env, "handleReceiveCallback");
    return status == OK || status == NO_MEMORY ? 1 : 0;
}

	{% endhighlight %}

	{% highlight java linenos %}  
	status_t NativeInputEventReceiver::consumeEvents(JNIEnv* env,
        bool consumeBatches, nsecs_t frameTime) {
	.......
        if (!skipCallbacks) {
            jobject inputEventObj;
            switch (inputEvent->getType()) {
            case AINPUT_EVENT_TYPE_KEY:
#if DEBUG_DISPATCH_CYCLE
                ALOGD("channel '%s' ~ Received key event.", getInputChannelName());
#endif
                inputEventObj = android_view_KeyEvent_fromNative(env,
                        static_cast<KeyEvent*>(inputEvent));
                break;

            case AINPUT_EVENT_TYPE_MOTION:
#if DEBUG_DISPATCH_CYCLE
                ALOGD("channel '%s' ~ Received motion event.", getInputChannelName());
#endif
                inputEventObj = android_view_MotionEvent_obtainAsCopy(env,
                        static_cast<MotionEvent*>(inputEvent));
                break;

            default:
                assert(false); // InputConsumer should prevent this from ever happening
                inputEventObj = NULL;
            }

            if (inputEventObj) {
#if DEBUG_DISPATCH_CYCLE
                ALOGD("channel '%s' ~ Dispatching input event.", getInputChannelName());
#endif
                env->CallVoidMethod(mReceiverObjGlobal,
                        gInputEventReceiverClassInfo.dispatchInputEvent, seq, inputEventObj);
                if (env->ExceptionCheck()) {
                    ALOGE("Exception dispatching input event.");
                    skipCallbacks = true;
                }
            } else {
                ALOGW("channel '%s' ~ Failed to obtain event object.", getInputChannelName());
                skipCallbacks = true;
            }
        }

        if (skipCallbacks) {
            mInputConsumer.sendFinishedSignal(seq, false);
        }
    }
}
	{% endhighlight %}
这里会回调到java层上的InputEventReceiver的dispatchInputEvent：


	{% highlight java linenos %}  
	// Called from native code.
    @SuppressWarnings("unused")
    private void dispatchInputEvent(int seq, InputEvent event) {
        mSeqMap.put(event.getSequenceNumber(), seq);
        onInputEvent(event);
    }
	{% endhighlight %}
这里的onInputEvent(event)方法已经被WindowInputEventReceiver复写了:

	{% highlight java linenos %}  
		@Override
        public void onInputEvent(InputEvent event) {
            enqueueInputEvent(event, this, 0, true);
        }


	{% endhighlight %}

这里往下翻一点就知道这个队列做了什么事情:

	{% highlight java linenos %}  
	private void deliverInputEvent(QueuedInputEvent q) {
        Trace.traceBegin(Trace.TRACE_TAG_VIEW, "deliverInputEvent");
        try {
            if (q.mEvent instanceof KeyEvent) {
                deliverKeyEvent(q);
            } else {
                final int source = q.mEvent.getSource();
                if ((source & InputDevice.SOURCE_CLASS_POINTER) != 0) {
                    deliverPointerEvent(q);
                } else if ((source & InputDevice.SOURCE_CLASS_TRACKBALL) != 0) {
                    deliverTrackballEvent(q);
                } else {
                    deliverGenericMotionEvent(q);
                }
            }
        } finally {
            Trace.traceEnd(Trace.TRACE_TAG_VIEW);
        }
    }

	{% endhighlight %}
这里讲底层的inputEvent分成各种不同的类型去区别对待.

这里就能看到View是如何接收事件的整个过程的


	{% highlight java linenos %}  {% endhighlight %}




### 结论

1.androd的底层实现是通过socket和共享内存的方式，这种写法也可以采用在我们自己的多进程通信上使用，值得学习
2.底层所有的event其实都是一样的，都是inputEvent，上层会根据source再分成keyEvent,MotionEvent等，用于不同的用处 
3.所有View的起点其实就是dispatchPointerEvent()，这个是分发事件的起点.


### 参考blog
[本文基于android-2.3.3_r1代码研究]: http://daemon369.github.io/android/2014/09/11/android-dispatchTouchEvent/  "本文基于android-2.3.3_r1代码研究"
[Android事件分发机制完全解析，带你从源码的角度彻底理解]: http://blog.csdn.net/guolin_blog/article/details/9153747 "Android事件分发机制完全解析，带你从源码的角度彻底理解"
[android-inputevent传递过程]:http://blog.pickbox.me/2014/05/22/android-inputevent传递过程（app端）/ "android-inputevent传递过程"

[yangming]:   
