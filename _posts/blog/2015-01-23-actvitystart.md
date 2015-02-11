---
layout: post
title: 学习Activity启动过程分析
description: This is android Project. 
category: blog
---
所有代码研究基于android4.2.2_R1 


##为何要研究Activity的启动过程:
1. Activity其实是android提供的一个壳,供我们去学习如何以比较快的速度去完成一个app，但是本着知其然，知其所以然的心态，Activity的启动方式是值得研究的.
2. Activity的启动过程中，我们可以看出activity与application是如何交互的，在哪些位置交互的.

## 简析Activity启动过程

![Alt text]( /images/android/android_activity_startservice.jpeg "Optional title")


上面这个图显示的一个外部调用ActivityManagerService去生成一个全新的Activity(包括生成这个Activity所在的application).这个图还包括了如何生成一个新的service。



###  在Launch点击了图片开始:
在Android系统中，应用程序是由Launcher启动起来的，其实，Launcher本身也是一个应用程序，其它的应用程序安装后，就会Launcher的界面上出现一个相应的图标，点击这个图标时，Launcher就会对应的应用程序启动起来。
 Launcher的源代码工程在packages/apps/Launcher2目录下，负责启动其它应用程序的源代码实现在src/com/android/launcher2/Launcher.java文件中

```java 
/**
* Default launcher application.
*/
public final class Launcher extends Activity
		implements View.OnClickListener, OnLongClickListener, LauncherModel.Callbacks, AllAppsView.Watcher {

	......

	/**
	* Launches the intent referred by the clicked shortcut.
	*
	* @param v The view representing the clicked shortcut.
	*/
	public void onClick(View v) {
		Object tag = v.getTag();
		if (tag instanceof ShortcutInfo) {
			// Open shortcut
			final Intent intent = ((ShortcutInfo) tag).intent;
			int[] pos = new int[2];
			v.getLocationOnScreen(pos);
			intent.setSourceBounds(new Rect(pos[0], pos[1],
				pos[0] + v.getWidth(), pos[1] + v.getHeight()));
			startActivitySafely(intent, tag);
		} else if (tag instanceof FolderInfo) {
			......
		} else if (v == mHandleView) {
			......
		}
	}

	void startActivitySafely(Intent intent, Object tag) {
		intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
		try {
			startActivity(intent);
		} catch (ActivityNotFoundException e) {
			......
		} catch (SecurityException e) {
			......
		}
	}

	......

}
```
一般的activity的AndroidManifest.xml为：

	{% highlight java linenos %} 
<activity android:name=".MainActivity"  
      android:label="@string/app_name">  
       <intent-filter>  
        <action android:name="android.intent.action.MAIN" />  
        <category android:name="android.intent.category.LAUNCHER" />  
    </intent-filter>  
</activity>  

	{% endhighlight %}
因此，这里的intent包含的信息为：action = "android.intent.action.Main"，category="android.intent.category.LAUNCHER", cmp="shy.luo.activity/.MainActivity"，表示它要启动的Activity为shy.luo.activity.MainActivity。

Intent.FLAG_ACTIVITY_NEW_TASK表示要在一个新的Task中启动这个Activity，注意，Task是Android系统中的概念，它不同于进程Process的概念。简单地说，一个Task是一系列Activity的集合，这个集合是以堆栈的形式来组织的，遵循后进先出的原则。事实上，Task是一个非常复杂的概念，有兴趣的读者可以到官网http://developer.android.com/guide/topics/manifest/activity-element.html查看相关的资料。这里，我们只要知道，这个MainActivity要在一个新的Task中启动就可以了。



调用的Activity的startActivity:

	{% highlight java linenos %} 
	 @Override
    public void startActivity(Intent intent) {
        startActivity(intent, null);
    }
	
	@Override
    public void startActivity(Intent intent, Bundle options) {
        if (options != null) {
            startActivityForResult(intent, -1, options);
        } else {
            // Note we want to go through this call for compatibility with
            // applications that may have overridden the method.
            startActivityForResult(intent, -1);
        }
    }

	public void startActivityForResult(Intent intent, int requestCode, Bundle options) {
        if (mParent == null) {
            Instrumentation.ActivityResult ar =
                mInstrumentation.execStartActivity(
                    this, mMainThread.getApplicationThread(), mToken, this,
                    intent, requestCode, options);
            if (ar != null) {
                mMainThread.sendActivityResult(
                    mToken, mEmbeddedID, requestCode, ar.getResultCode(),
                    ar.getResultData());
            }
            if (requestCode >= 0) {
                // If this start is requesting a result, we can avoid making
                // the activity visible until the result is received.  Setting
                // this code during onCreate(Bundle savedInstanceState) or onResume() will keep the
                // activity hidden during this time, to avoid flickering.
                // This can only be done when a result is requested because
                // that guarantees we will get information back when the
                // activity is finished, no matter what happens to it.
                mStartedActivity = true;
            }

        } 
			......
   }
	{% endhighlight %}
第一次mParent为空，因此调用的mInstrumentation.execStartActivity,类型为mInstrumentation。这里的mMainThread也是Activity类的成员变量，它的类型是ActivityThread，它代表的是应用程序的主线程。

这里的mToken也是Activity类的成员变量，它是一个Binder对象的远程接口。

看下Instrumentation的代码:

	{% highlight java linenos %} 
	public ActivityResult execStartActivity(
            Context who, IBinder contextThread, IBinder token, Activity target,
            Intent intent, int requestCode, Bundle options) {
        IApplicationThread whoThread = (IApplicationThread) contextThread;
		......        
        try {
            intent.setAllowFds(false);
            intent.migrateExtraStreamToClipData();
            int result = ActivityManagerNative.getDefault()
                .startActivity(whoThread, intent,
                        intent.resolveTypeIfNeeded(who.getContentResolver()),
                        token, target != null ? target.mEmbeddedID : null,
                        requestCode, 0, null, null, options);
            checkStartActivityResult(result, intent);
        } catch (RemoteException e) {
        }
        return null;
    }

	{% endhighlight %}
 这里的ActivityManagerNative.getDefault返回ActivityManagerService的远程接口，即ActivityManagerProxy接口。

我们看ActivityManagerService.startActivity

	{% highlight java linenos %} 
	public final int startActivity(IApplicationThread caller,
            Intent intent, String resolvedType, IBinder resultTo,
            String resultWho, int requestCode, int startFlags,
            String profileFile, ParcelFileDescriptor profileFd, Bundle options) {
        return startActivityAsUser(caller, intent, resolvedType, resultTo, resultWho, requestCode,
                startFlags, profileFile, profileFd, options, UserHandle.getCallingUserId());
    }

    public final int startActivityAsUser(IApplicationThread caller,
            Intent intent, String resolvedType, IBinder resultTo,
            String resultWho, int requestCode, int startFlags,
            String profileFile, ParcelFileDescriptor profileFd, Bundle options, int userId) {
        enforceNotIsolatedCaller("startActivity");
        userId = handleIncomingUser(Binder.getCallingPid(), Binder.getCallingUid(), userId,
                false, true, "startActivity", null);
        return mMainStack.startActivityMayWait(caller, -1, intent, resolvedType,
                resultTo, resultWho, requestCode, startFlags, profileFile, profileFd,
                null, null, options, userId);
    }

	{% endhighlight %}
这里只是简单地将操作转发给成员变量mMainStack的startActivityMayWait函数，这里的mMainStack的类型为ActivityStack。
查看startActivityMayWait

	{% highlight java linenos %} 
	final int startActivityMayWait(IApplicationThread caller, int callingUid,
            Intent intent, String resolvedType, IBinder resultTo,
            String resultWho, int requestCode, int startFlags, String profileFile,
            ParcelFileDescriptor profileFd, WaitResult outResult, Configuration config,
            Bundle options, int userId) {

		// Don't modify the client's object!
        intent = new Intent(intent);

        // Collect information about the target of the Intent.
        ActivityInfo aInfo = resolveActivity(intent, resolvedType, startFlags,
                profileFile, profileFd, userId);
		.......
		try {
        	ResolveInfo rInfo =
			AppGlobals.getPackageManager().resolveIntent(
     			ntent, null,
                PackageManager.MATCH_DEFAULT_ONLY
                 | ActivityManagerService.STOCK_PM_FLAGS, userId);
 			Info = rInfo != null ? rInfo.activityInfo : null;
            aInfo = mService.getActivityInfoForUser(aInfo, userId);
            } catch (RemoteException e) {
			aInfo = null;
		}
        int res = startActivityLocked(caller, intent, resolvedType,
                    aInfo, resultTo, resultWho, requestCode, callingPid, callingUid,
                    startFlags, options, componentSpecified, null);


		return res;  

	}

	{% endhighlight %}
这里的代码真的很长，但是大部分不用关心：
要注意的是·

	{% highlight java linenos %} 
	try {
        	ResolveInfo rInfo =
			AppGlobals.getPackageManager().resolveIntent(
     			ntent, null,
                PackageManager.MATCH_DEFAULT_ONLY
                 | ActivityManagerService.STOCK_PM_FLAGS, userId);
 			Info = rInfo != null ? rInfo.activityInfo : null;
            aInfo = mService.getActivityInfoForUser(aInfo, userId);
            } catch (RemoteException e) {
			}

	{% endhighlight %}
这里的aInfo就是AndroidManifest.xml里面配置的。

 接下去就调用startActivityLocked进一步处理了。





	{% highlight java linenos %} 
final int startActivityLocked(IApplicationThread caller,
            Intent intent, String resolvedType, ActivityInfo aInfo, IBinder resultTo,
            String resultWho, int requestCode,
            int callingPid, int callingUid, int startFlags, Bundle options,
            boolean componentSpecified, ActivityRecord[] outActivity) {

        int err = ActivityManager.START_SUCCESS;

		 if (caller != null) {  
            callerApp = mService.getRecordForAppLocked(caller);  
            if (callerApp != null) {  
                callingPid = callerApp.pid;  
                callingUid = callerApp.info.uid;  
            } else {  
                ......  
            }  
        }  

       ......
    
        ActivityRecord sourceRecord = null;
        ActivityRecord resultRecord = null;
        if (resultTo != null) {
            int index = indexOfTokenLocked(resultTo);
            if (DEBUG_RESULTS) Slog.v(
                TAG, "Will send result to " + resultTo + " (index " + index + ")");
            if (index >= 0) {
                sourceRecord = mHistory.get(index);
                if (requestCode >= 0 && !sourceRecord.finishing) {
                    resultRecord = sourceRecord;
                }
            }
        }

        int launchFlags = intent.getFlags();

        if ((launchFlags&Intent.FLAG_ACTIVITY_FORWARD_RESULT) != 0
                && sourceRecord != null) {
            // Transfer the result target from the source activity to the new
            // one being started, including any failures.
            if (requestCode >= 0) {
                ActivityOptions.abort(options);
                return ActivityManager.START_FORWARD_AND_REQUEST_CONFLICT;
            }
            resultRecord = sourceRecord.resultTo;
            resultWho = sourceRecord.resultWho;
            requestCode = sourceRecord.requestCode;
            sourceRecord.resultTo = null;
            if (resultRecord != null) {
                resultRecord.removeResultsLocked(
                    sourceRecord, resultWho, requestCode);
            }
        }

        if (err == ActivityManager.START_SUCCESS && intent.getComponent() == null) {
            // We couldn't find a class that can handle the given Intent.
            // That's the end of that!
            err = ActivityManager.START_INTENT_NOT_RESOLVED;
        }

        if (err == ActivityManager.START_SUCCESS && aInfo == null) {
            // We couldn't find the specific class specified in the Intent.
            // Also the end of the line.
            err = ActivityManager.START_CLASS_NOT_FOUND;
        }

        if (err != ActivityManager.START_SUCCESS) {
            if (resultRecord != null) {
                sendActivityResultLocked(-1,
                    resultRecord, resultWho, requestCode,
                    Activity.RESULT_CANCELED, null);
            }
            mDismissKeyguardOnNextActivity = false;
            ActivityOptions.abort(options);
            return err;
        }
			......

        ActivityRecord r = new ActivityRecord(mService, this, callerApp, callingUid,
                intent, resolvedType, aInfo, mService.mConfiguration,
                resultRecord, resultWho, requestCode, componentSpecified);
        if (outActivity != null) {
            outActivity[0] = r;
        }

        if (mMainStack) {
            if (mResumedActivity == null
                    || mResumedActivity.info.applicationInfo.uid != callingUid) {
                if (!mService.checkAppSwitchAllowedLocked(callingPid, callingUid, "Activity start")) {
                    PendingActivityLaunch pal = new PendingActivityLaunch();
                    pal.r = r;
                    pal.sourceRecord = sourceRecord;
                    pal.startFlags = startFlags;
                    mService.mPendingActivityLaunches.add(pal);
                    mDismissKeyguardOnNextActivity = false;
                    ActivityOptions.abort(options);
                    return ActivityManager.START_SWITCHES_CANCELED;
                }
            }
        
            if (mService.mDidAppSwitch) {
                // This is the second allowed switch since we stopped switches,
                // so now just generally allow switches.  Use case: user presses
                // home (switches disabled, switch to home, mDidAppSwitch now true);
                // user taps a home icon (coming from home so allowed, we hit here
                // and now allow anyone to switch again).
                mService.mAppSwitchesAllowedTime = 0;
            } else {
                mService.mDidAppSwitch = true;
            }
         
            mService.doPendingActivityLaunchesLocked(false);
        }
        
        err = startActivityUncheckedLocked(r, sourceRecord,
                startFlags, true, options);
        if (mDismissKeyguardOnNextActivity && mPausingActivity == null) {
            // Someone asked to have the keyguard dismissed on the next
            // activity start, but we are not actually doing an activity
            // switch...  just dismiss the keyguard now, because we
            // probably want to see whatever is behind it.
            mDismissKeyguardOnNextActivity = false;
            mService.mWindowManager.dismissKeyguard();
        }
        return err;
    }
	{% endhighlight %}
之前说的caller就是调用者的进程信息，并保存在callerApp变量中,我们这里就是Launcher的进程信息。
resultTo则是调用的activity的信息。最终保存在sourceRecord中。
我们要创建Activity前会创建ActivityRecord.
 接着调用startActivityUncheckedLocked函数进行下一步操作。

{% highlight java linenos %} 
final int startActivityUncheckedLocked(ActivityRecord r,
            ActivityRecord sourceRecord, int startFlags, boolean doResume,
            Bundle options) {
        final Intent intent = r.intent;
        final int callingUid = r.launchedFromUid;

        int launchFlags = intent.getFlags();
       	
		...... 
       
        if (sourceRecord == null) {
            // This activity is not being started from another...  in this
            // case we -always- start a new task.
            launchFlags |= Intent.FLAG_ACTIVITY_NEW_TASK;
            
        } else if (sourceRecord.launchMode == ActivityInfo.LAUNCH_SINGLE_INSTANCE) {
            // The original activity who is starting us is running as a single
            // instance...  this new activity it is starting must go on its
            // own task.
            launchFlags |= Intent.FLAG_ACTIVITY_NEW_TASK;
        } else if (r.launchMode == ActivityInfo.LAUNCH_SINGLE_INSTANCE
                || r.launchMode == ActivityInfo.LAUNCH_SINGLE_TASK) {
            // The activity being started is a single instance...  it always
            // gets launched into its own task.
            launchFlags |= Intent.FLAG_ACTIVITY_NEW_TASK;
        }

        if (r.resultTo != null && (launchFlags&Intent.FLAG_ACTIVITY_NEW_TASK) != 0) {
            // For whatever reason this activity is being launched into a new
            // task...  yet the caller has requested a result back.  Well, that
            // is pretty messed up, so instead immediately send back a cancel
            // and let the new task continue launched as normal without a
            // dependency on its originator.
            Slog.w(TAG, "Activity is launching as a new task, so cancelling activity result.");
            sendActivityResultLocked(-1,
                    r.resultTo, r.resultWho, r.requestCode,
                Activity.RESULT_CANCELED, null);
            r.resultTo = null;
        }

        boolean addingToTask = false;
        boolean movedHome = false;
        TaskRecord reuseTask = null;
        if (((launchFlags&Intent.FLAG_ACTIVITY_NEW_TASK) != 0 &&
                (launchFlags&Intent.FLAG_ACTIVITY_MULTIPLE_TASK) == 0)
                || r.launchMode == ActivityInfo.LAUNCH_SINGLE_TASK
                || r.launchMode == ActivityInfo.LAUNCH_SINGLE_INSTANCE) {
            // If bring to front is requested, and no result is requested, and
            // we can find a task that was started with this same
            // component, then instead of launching bring that one to the front.
            if (r.resultTo == null) {
				......
	        }
	}


        if (r.packageName != null) {
            // If the activity being launched is the same as the one currently
            // at the top, then we need to check if it should only be launched
            // once.
            ActivityRecord top = topRunningNonDelayedActivityLocked(notTop);
            if (top != null && r.resultTo == null) {
                if (top.realActivity.equals(r.realActivity) && top.userId == r.userId) {
                    if (top.app != null && top.app.thread != null) {
                        if ((launchFlags&Intent.FLAG_ACTIVITY_SINGLE_TOP) != 0
                            || r.launchMode == ActivityInfo.LAUNCH_SINGLE_TOP
                            || r.launchMode == ActivityInfo.LAUNCH_SINGLE_TASK) {
						......
                            ActivityOptions.abort(options);
                            if ((startFlags&ActivityManager.START_FLAG_ONLY_IF_NEEDED) != 0) {
                                // We don't need to start a new activity, and
                                // the client said not to do anything if that
                                // is the case, so this is it!
                                return ActivityManager.START_RETURN_INTENT_TO_CALLER;
                            }
                            top.deliverNewIntentLocked(callingUid, r.intent);
                            return ActivityManager.START_DELIVERED_TO_TOP;
                        }
                    }
                }
            }

        } else {
            if (r.resultTo != null) {
                sendActivityResultLocked(-1,
                        r.resultTo, r.resultWho, r.requestCode,
                    Activity.RESULT_CANCELED, null);
            }
            ActivityOptions.abort(options);
            return ActivityManager.START_CLASS_NOT_FOUND;
        }

        boolean newTask = false;
        boolean keepCurTransition = false;

        // Should this be considered a new task?
        if (r.resultTo == null && !addingToTask
                && (launchFlags&Intent.FLAG_ACTIVITY_NEW_TASK) != 0) {
            if (reuseTask == null) {
                // todo: should do better management of integers.
                mService.mCurTask++;
                if (mService.mCurTask <= 0) {
                    mService.mCurTask = 1;
                }
                r.setTask(new TaskRecord(mService.mCurTask, r.info, intent), null, true);
                if (DEBUG_TASKS) Slog.v(TAG, "Starting new activity " + r
                        + " in new task " + r.task);
            } else {
                r.setTask(reuseTask, reuseTask, true);
            }
            newTask = true;
            if (!movedHome) {
                moveHomeToFrontFromLaunchLocked(launchFlags);
            }
            
        } else if (sourceRecord != null) {
            if (!addingToTask &&
                    (launchFlags&Intent.FLAG_ACTIVITY_CLEAR_TOP) != 0) {
                // In this case, we are adding the activity to an existing
                // task, but the caller has asked to clear that task if the
                // activity is already running.
                ActivityRecord top = performClearTaskLocked(
                        sourceRecord.task.taskId, r, launchFlags);
                keepCurTransition = true;
                if (top != null) {
                    logStartActivity(EventLogTags.AM_NEW_INTENT, r, top.task);
                    top.deliverNewIntentLocked(callingUid, r.intent);
                    // For paranoia, make sure we have correctly
                    // resumed the top activity.
                    if (doResume) {
                        resumeTopActivityLocked(null);
                    }
                    ActivityOptions.abort(options);
                    return ActivityManager.START_DELIVERED_TO_TOP;
                }
            } else if (!addingToTask &&
                    (launchFlags&Intent.FLAG_ACTIVITY_REORDER_TO_FRONT) != 0) {
                ......
        } else {
            ......
        }

        mService.grantUriPermissionFromIntentLocked(callingUid, r.packageName,
                intent, r.getUriPermissionsLocked());

        if (newTask) {
            EventLog.writeEvent(EventLogTags.AM_CREATE_TASK, r.userId, r.task.taskId);
        }
        logStartActivity(EventLogTags.AM_CREATE_ACTIVITY, r, r.task);
        startActivityLocked(r, newTask, doResume, keepCurTransition, options);
        return ActivityManager.START_SUCCESS;
    }
{% endhighlight %}
这个函数更长。我们来讲解下运行过程：
1. 函数首先获得intent的标志值，保存在launchFlags变量中。
2. 这个intent的标志值的位Intent.FLAG_ACTIVITY_NO_USER_ACTION没有置位，因此 ，成员变量mUserLeaving的值为true。
3. 这个intent的标志值的位Intent.FLAG_ACTIVITY_PREVIOUS_IS_TOP也没有置位，因此，变量notTop的值为null。
4. 由于在这个例子的AndroidManifest.xml文件中，MainActivity没有配置launchMode属值，因此，这里的r.launchMode为默认值0，表示以标准（Standard，或者称为ActivityInfo.LAUNCH_MULTIPLE）的方式来启动这个Activity。Activity的启动方式有四种，其余三种分别是ActivityInfo.LAUNCH_SINGLE_INSTANCE、ActivityInfo.LAUNCH_SINGLE_TASK和ActivityInfo.LAUNCH_SINGLE_TOP，具体可以参考官方网站。
5. 传进来的参数r.resultTo为null，表示Launcher不需要等这个即将要启动的MainActivity的执行结果
6. 由于这个intent的标志值的位Intent.FLAG_ACTIVITY_NEW_TASK被置位，而且Intent.FLAG_ACTIVITY_MULTIPLE_TASK没有置位，因此，下面的if语句会被执行：


{% highlight java linenos %} 
if (((launchFlags&Intent.FLAG_ACTIVITY_NEW_TASK) != 0 &&
                (launchFlags&Intent.FLAG_ACTIVITY_MULTIPLE_TASK) == 0)
                || r.launchMode == ActivityInfo.LAUNCH_SINGLE_TASK
                || r.launchMode == ActivityInfo.LAUNCH_SINGLE_INSTANCE) {

	if (r.resultTo == null) {  
        // See if there is a task to bring to the front.  If this is  
        // a SINGLE_INSTANCE activity, there can be one and only one  
        // instance of it in the history, and it is always in its own  
        // unique task, so we do a special search.  
        ActivityRecord taskTop = r.launchMode != ActivityInfo.LAUNCH_SINGLE_INSTANCE  
            ? findTaskLocked(intent, r.info)  
            : findActivityLocked(intent, r.info);  
        if (taskTop != null) {  
            ......  
        }  
    }  
   }  
{% endhighlight %}
7. 这段代码的逻辑是查看一下，当前有没有Task可以用来执行这个Activity。由于r.launchMode的值不为ActivityInfo.LAUNCH_SINGLE_INSTANCE，因此，它通过findTaskLocked函数来查找存不存这样的Task，这里返回的结果是null，即taskTop为null，因此，需要创建一个新的Task来启动这个Activity。
8. 执行到这里，我们知道，要在一个新的Task里面来启动这个Activity了，于是新创建一个Task：


{% highlight java linenos %} 
if (r.resultTo == null && !addingToTask
                && (launchFlags&Intent.FLAG_ACTIVITY_NEW_TASK) != 0) {
            if (reuseTask == null) {
                // todo: should do better management of integers.
                mService.mCurTask++;
                if (mService.mCurTask <= 0) {
                    mService.mCurTask = 1;
                }
                r.setTask(new TaskRecord(mService.mCurTask, r.info, intent), null, true);
                if (DEBUG_TASKS) Slog.v(TAG, "Starting new activity " + r
                        + " in new task " + r.task);
            } else {
                r.setTask(reuseTask, reuseTask, true);
            }
            newTask = true;
            if (!movedHome) {
                moveHomeToFrontFromLaunchLocked(launchFlags);
            }
            
        }

{% endhighlight %}
新建的Task保存在r.task域中，同时，添加到mService中去，这里的mService就是ActivityManagerService了。

分析函数,startActivityLocked.

	{% highlight java linenos %} 
	private final void startActivityLocked(ActivityRecord r, boolean newTask,
            boolean doResume, boolean keepCurTransition, Bundle options) {
        final int NH = mHistory.size();
        int addPos = -1;
        
		    .....
        // Place a new activity at top of stack, so it is next to interact
        // with the user.
        if (addPos < 0) {
            addPos = NH;
        }
        
        // If we are not placing the new activity frontmost, we do not want
        // to deliver the onUserLeaving callback to the actual frontmost
        // activity
        if (addPos < NH) {
            mUserLeaving = false;
            if (DEBUG_USER_LEAVING) Slog.v(TAG, "startActivity() behind front, mUserLeaving=false");
        }
        
        mHistory.add(addPos, r);
        r.putInHistory();
        r.frontOfTask = newTask;
        if (NH > 0) {
            // We want to show the starting preview window if we are
            // switching to a new task, or the next activity's process is
            // not currently running.
            r.updateOptionsLocked(options);
					.......
            mService.mWindowManager.addAppToken(
                    addPos, r.appToken, r.task.taskId, r.info.screenOrientation, r.fullscreen,
                    (r.info.flags & ActivityInfo.FLAG_SHOW_ON_LOCK_SCREEN) != 0);
            boolean doShow = true;
            if (SHOW_APP_STARTING_PREVIEW && doShow) {
                // Figure out if we are transitioning from another activity that is
                // "has the same starting icon" as the next one.  This allows the
                // window manager to keep the previous window it had previously
                // created, if it still had one.
                ActivityRecord prev = mResumedActivity;
                if (prev != null) {
                    // We don't want to reuse the previous starting preview if:
                    // (1) The current activity is in a different task.
                    if (prev.task != r.task) prev = null;
                    // (2) The current activity is already displayed.
                    else if (prev.nowVisible) prev = null;
                }
                mService.mWindowManager.setAppStartingWindow(
                        r.appToken, r.packageName, r.theme,
                        mService.compatibilityInfoForPackageLocked(
                                r.info.applicationInfo), r.nonLocalizedLabel,
                        r.labelRes, r.icon, r.windowFlags,
                        prev != null ? prev.appToken : null, showStartingIcon);
            }
        } else {
            // If this is the first activity, don't do any fancy animations,
            // because there is nothing for it to animate on top of.
            mService.mWindowManager.addAppToken(addPos, r.appToken, r.task.taskId,
                    r.info.screenOrientation, r.fullscreen,
                    (r.info.flags & ActivityInfo.FLAG_SHOW_ON_LOCK_SCREEN) != 0);
            ActivityOptions.abort(options);
        }
        if (VALIDATE_TOKENS) {
            validateAppTokensLocked();
        }

        if (doResume) {
            resumeTopActivityLocked(null);
        }
    }

	{% endhighlight %}
这里的NH表示当前系统中历史任务的个数，这里肯定是大于0，因为Launcher已经跑起来了。当NH>0时，并且现在要切换新任务时，要做一些任务切的界面操作，这段代码我们就不看了，这里不会影响到下面启Activity的过程，有兴趣的读取可以自己研究一下。

	{% highlight java linenos %}
public class ActivityStack {

	......

	/**
	* Ensure that the top activity in the stack is resumed.
	*
	* @param prev The previously resumed activity, for when in the process
	* of pausing; can be null to call from elsewhere.
	*
	* @return Returns true if something is being resumed, or false if
	* nothing happened.
	*/
	final boolean resumeTopActivityLocked(ActivityRecord prev) {
		// Find the first activity that is not finishing.
		ActivityRecord next = topRunningActivityLocked(null);

		// Remember how we'll process this pause/resume situation, and ensure
		// that the state is reset however we wind up proceeding.
		final boolean userLeaving = mUserLeaving;
		mUserLeaving = false;

		if (next == null) {
			......
		}

		next.delayedResume = false;

		// If the top activity is the resumed one, nothing to do.
		if (mResumedActivity == next && next.state == ActivityState.RESUMED) {
			......
		}

		// If we are sleeping, and there is no resumed activity, and the top
		// activity is paused, well that is the state we want.
		if ((mService.mSleeping || mService.mShuttingDown)
			&& mLastPausedActivity == next && next.state == ActivityState.PAUSED) {
			......
		}

		......

		// If we are currently pausing an activity, then don't do anything
		// until that is done.
		if (mPausingActivity != null) {
			......
		}

		......

		// We need to start pausing the current activity so the top one
		// can be resumed...
		if (mResumedActivity != null) {
			......
			startPausingLocked(userLeaving, false);
			return true;
		}

		......
	}

	......

}

{% endhighlight %}
分析代码：
1. 函数先通过调用topRunningActivityLocked函数获得堆栈顶端的Activity，这里就是MainActivity了。
2. 接下来把mUserLeaving的保存在本地变量userLeaving中，然后重新设置为false，这里的userLeaving为true。
3. 这里的mResumedActivity为Launcher，因为Launcher是当前正被执行的Activity。
4. 当我们处理休眠状态时，mLastPausedActivity保存堆栈顶端的Activity，因为当前不是休眠状态，所以mLastPausedActivity为null。
5. 这样我们理解后面的代码就明白了 	

{% highlight java linenos %} 
    // If the top activity is the resumed one, nothing to do.
    if (mResumedActivity == next && next.state == ActivityState.RESUMED) {
	......
    }

    // If we are sleeping, and there is no resumed activity, and the top
    // activity is paused, well that is the state we want.
    if ((mService.mSleeping || mService.mShuttingDown)
	&& mLastPausedActivity == next && next.state == ActivityState.PAUSED) {
	......
    }
{% endhighlight %}

6. 它首先看要启动的Activity是否就是当前处理Resumed状态的Activity，如果是的话，那就什么都不用做，直接返回就可以了；否则再看一下系统当前是否休眠状态，如果是的话，再看看要启动的Activity是否就是当前处于堆栈顶端的Activity，如果是的话，也是什么都不用做。

7. 上面两个条件都不满足，因此，在继续往下执行之前，首先要把当处于Resumed状态的Activity推入Paused状态，然后才可以启动新的Activity。但是在将当前这个Resumed状态的Activity推入Paused状态之前，首先要看一下当前是否有Activity正在进入Pausing状态，如果有的话，当前这个Resumed状态的Activity就要稍后才能进入Paused状态了，这样就保证了所有需要进入Paused状态的Activity串行处理。
8. 这里没有处于Pausing状态的Activity，即mPausingActivity为null，而且mResumedActivity也不为null，于是就调用startPausingLocked函数把Launcher推入Paused状态去了。

查看函数ActivityStack.startPausingLocked:

{% highlight java linenos %} 
public class ActivityStack {

	......

	private final void startPausingLocked(boolean userLeaving, boolean uiSleeping) {
		if (mPausingActivity != null) {
			......
		}
		ActivityRecord prev = mResumedActivity;
		if (prev == null) {
			......
		}
		......
		mResumedActivity = null;
		mPausingActivity = prev;
		mLastPausedActivity = prev;
		prev.state = ActivityState.PAUSING;
		......

		if (prev.app != null && prev.app.thread != null) {
			......
			try {
				......
				prev.app.thread.schedulePauseActivity(prev, prev.finishing, userLeaving,
					prev.configChangeFlags);
				......
			} catch (Exception e) {
				......
			}
		} else {
			......
		}

		......
	
	}

	......

}
{% endhighlight %}
1. 函数首先把mResumedActivity保存在本地变量prev中。在上一步中，说到mResumedActivity就是Launcher，因此，这里把Launcher进程中的ApplicationThread对象取出来，通过它来通知Launcher这个Activity它要进入Paused状态了。当然，这里的prev.app.thread是一个ApplicationThread对象的远程接口，通过调用这个远程接口的schedulePauseActivity来通知Launcher进入Paused状态。
2. 参数prev.finishing表示prev所代表的Activity是否正在等待结束的Activity列表中，由于Laucher这个Activity还没结束，所以这里为false；参数prev.configChangeFlags表示哪些config发生了变化，这里我们不关心它的值。
3. 这里的调用的ApplicationThreadProxy.schedulePauseActivity,对应的service端代码为ApplicationThread.schedulePauseActivity.

{% highlight java linenos %} 
public final class ActivityThread {
	
	......

	private final class ApplicationThread extends ApplicationThreadNative {
		
		......

		public final void schedulePauseActivity(IBinder token, boolean finished,
				boolean userLeaving, int configChanges) {
			queueOrSendMessage(
				finished ? H.PAUSE_ACTIVITY_FINISHING : H.PAUSE_ACTIVITY,
				token,
				(userLeaving ? 1 : 0),
				configChanges);
		}

		......

	}

	// if the thread hasn't started yet, we don't have the handler, so just
    // save the messages until we're ready.
    private void queueOrSendMessage(int what, Object obj) {
        queueOrSendMessage(what, obj, 0, 0);
    }

	private void queueOrSendMessage(int what, Object obj, int arg1, int arg2) {
        synchronized (this) {
            if (DEBUG_MESSAGES) Slog.v(
                TAG, "SCHEDULE " + what + " " + mH.codeToString(what)
                + ": " + arg1 + " / " + obj);
            Message msg = Message.obtain();
            msg.what = what;
            msg.obj = obj;
            msg.arg1 = arg1;
            msg.arg2 = arg2;
            mH.sendMessage(msg);
        }
    }

	......
	private class H extends Handler {


		public void handleMessage(Message msg) {
		......
				case PAUSE_ACTIVITY:
                    Trace.traceBegin(Trace.TRACE_TAG_ACTIVITY_MANAGER, "activityPause");
                    handlePauseActivity((IBinder)msg.obj, false, msg.arg1 != 0, msg.arg2);
                    maybeSnapshot();
                    Trace.traceEnd(Trace.TRACE_TAG_ACTIVITY_MANAGER);
                    break;
				case PAUSE_ACTIVITY_FINISHING:
                    Trace.traceBegin(Trace.TRACE_TAG_ACTIVITY_MANAGER, "activityPause");
                    handlePauseActivity((IBinder)msg.obj, true, msg.arg1 != 0, msg.arg2);
                    Trace.traceEnd(Trace.TRACE_TAG_ACTIVITY_MANAGER);
                    break;
		......

		}
	}

	private void handlePauseActivity(IBinder token, boolean finished,
            boolean userLeaving, int configChanges) {
        ActivityClientRecord r = mActivities.get(token);
        if (r != null) {
            //Slog.v(TAG, "userLeaving=" + userLeaving + " handling pause of " + r);
            if (userLeaving) {
                performUserLeavingActivity(r);
            }

            r.activity.mConfigChangeFlags |= configChanges;
            performPauseActivity(token, finished, r.isPreHoneycomb());

            // Make sure any pending writes are now committed.
            if (r.isPreHoneycomb()) {
                QueuedWork.waitToFinish();
            }

            // Tell the activity manager we have paused.
            try {
                ActivityManagerNative.getDefault().activityPaused(token);
            } catch (RemoteException ex) {
            }
        }
    }

	......

}

{% endhighlight %}
最终要看的函数其实就是handlePauseActivity,函数首先将Binder引用token转换成ActivityRecord的远程接口ActivityClientRecord，然后做了三个事情:
1. 如果userLeaving为true，则通过调用performUserLeavingActivity函数来调用Activity.onUserLeaveHint通知Activity，用户要离开它了.
2. 调用performPauseActivity函数来调用Activity.onPause函数，我们知道，在Activity的生命周期中，当它要让位于其它的Activity时，系统就会调用它的onPause函数.
3. 它通知ActivityManagerService，这个Activity已经进入Paused状态了，ActivityManagerService现在可以完成未竟的事情，即启动MainActivity了。

这里的ActivityManagerNative.getDefault() 最终指向的是ActivityManagerService。
ActivityManagerService.activityPaused():

{% highlight java linenos %} 
	public final void activityPaused(IBinder token) {
        final long origId = Binder.clearCallingIdentity();
        mMainStack.activityPaused(token, false);
        Binder.restoreCallingIdentity(origId);
    }
{% endhighlight %}
又再次进入到ActivityStack类中，执行activityPaused函数。
这个函数定义在frameworks/base/services/java/com/android/server/am/ActivityStack.java文件中

{% highlight java linenos %} 
	final void activityPaused(IBinder token, boolean timeout) {
        if (DEBUG_PAUSE) Slog.v(
            TAG, "Activity paused: token=" + token + ", timeout=" + timeout);

        ActivityRecord r = null;

        synchronized (mService) {
            int index = indexOfTokenLocked(token);
            if (index >= 0) {
                r = mHistory.get(index);
                mHandler.removeMessages(PAUSE_TIMEOUT_MSG, r);
                if (mPausingActivity == r) {
                    if (DEBUG_STATES) Slog.v(TAG, "Moving to PAUSED: " + r
                            + (timeout ? " (due to timeout)" : " (pause complete)"));
                    r.state = ActivityState.PAUSED;
                    completePauseLocked();
                } else {
                    EventLog.writeEvent(EventLogTags.AM_FAILED_TO_PAUSE,
                            r.userId, System.identityHashCode(r), r.shortComponentName, 
                            mPausingActivity != null
                                ? mPausingActivity.shortComponentName : "(none)");
                }
            }
        }
    }
{% endhighlight %}
这里通过参数token在mHistory列表中得到ActivityRecord，从上面我们知道，这个ActivityRecord代表的是Launcher这个Activity,之前将Launcher这个Activity的信息保存在mPausingActivity中，因此，这里mPausingActivity等于r，于是，执行completePauseLocked操作。
ActivityStack.completePauseLocked


{% highlight java linenos %} 
public class ActivityStack {

	......

	private final void completePauseLocked() {
		ActivityRecord prev = mPausingActivity;
		
		......

		if (prev != null) {

			......

			mPausingActivity = null;
		}

		if (!mService.mSleeping && !mService.mShuttingDown) {
			resumeTopActivityLocked(prev);
		} else {
			......
		}

		......
	}

	......

}
{% endhighlight %}

函数首先把mPausingActivity变量清空，因为现在不需要它了，然后调用resumeTopActivityLokced进一步操作，它传入的参数即为代表Launcher这个Activity的ActivityRecord。

再次看看我们熟悉的resumeTopActivityLocked.

{% highlight java linenos %} 
public class ActivityStack {

	......

	final boolean resumeTopActivityLocked(ActivityRecord prev) {
		......

		// Find the first activity that is not finishing.
		ActivityRecord next = topRunningActivityLocked(null);

		// Remember how we'll process this pause/resume situation, and ensure
		// that the state is reset however we wind up proceeding.
		final boolean userLeaving = mUserLeaving;
		mUserLeaving = false;

		......

		next.delayedResume = false;

		// If the top activity is the resumed one, nothing to do.
		if (mResumedActivity == next && next.state == ActivityState.RESUMED) {
			......
			return false;
		}

		// If we are sleeping, and there is no resumed activity, and the top
		// activity is paused, well that is the state we want.
		if ((mService.mSleeping || mService.mShuttingDown)
			&& mLastPausedActivity == next && next.state == ActivityState.PAUSED) {
			......
			return false;
		}

		.......


		// We need to start pausing the current activity so the top one
		// can be resumed...
		if (mResumedActivity != null) {
			......
			return true;
		}

		......


		if (next.app != null && next.app.thread != null) {
			......

		} else {
			......
			startSpecificActivityLocked(next, true, true);
		}

		return true;
	}
	......
}

{% endhighlight %}
我们知道，当前在堆栈顶端的Activity为我们即将要启动的MainActivity，这里通过调用topRunningActivityLocked将它取回来，保存在next变量中。之前最后一个Resumed状态的Activity，即Launcher，到了这里已经处于Paused状态了，因此，mResumedActivity为null。最后一个处于Paused状态的Activity为Launcher，因此，这里的mLastPausedActivity就为Launcher。前面我们为MainActivity创建了ActivityRecord后，它的app域一直保持为null。有了这些信息后，上面这段代码就容易理解了，它最终调用startSpecificActivityLocked进行下一步操作。
查看 startSpecificActivityLocked函数:

{% highlight java linenos %} 
public class ActivityStack {

	......

	private final void startSpecificActivityLocked(ActivityRecord r,
			boolean andResume, boolean checkConfig) {
		// Is this activity's application already running?
		ProcessRecord app = mService.getProcessRecordLocked(r.processName,
			r.info.applicationInfo.uid);

		......

		if (app != null && app.thread != null) {
			try {
				realStartActivityLocked(r, app, andResume, checkConfig);
				return;
			} catch (RemoteException e) {
				......
			}
		}

		mService.startProcessLocked(r.processName, r.info.applicationInfo, true, 0,
			"activity", r.intent.getComponent(), false);
	}
	......
}

{% endhighlight %}

由于第一次启动这个应用APP，所以app为null，执行mService.startProcessLocked.
也就是调用的ActivityManagerService.startProcessLocked.
查看函数startProcessLocked.

{% highlight java linenos %} 
	public final class ActivityManagerService extends ActivityManagerNative
		implements Watchdog.Monitor, BatteryStatsImpl.BatteryCallback {

	......

	final ProcessRecord startProcessLocked(String processName,
			ApplicationInfo info, boolean knownToBeDead, int intentFlags,
			String hostingType, ComponentName hostingName, boolean allowWhileBooting) {

		ProcessRecord app = getProcessRecordLocked(processName, info.uid);
		
		......

		String hostingNameStr = hostingName != null
			? hostingName.flattenToShortString() : null;

		......

		if (app == null) {
			app = newProcessRecordLocked(null, info, processName);
			mProcessNames.put(processName, info.uid, app);
		} else {
			// If this is a new package in the process, add the package to the list
			app.addPackage(info.packageName);
		}

		......

		startProcessLocked(app, hostingType, hostingNameStr);
		return (app.pid != 0) ? app : null;
	}
	......
}
{% endhighlight %}
这里会根据pid跟processname去检查ProcessRecord是否存在，如果不存在则生成新的record.我们这里是不存在的.所以会new出新的record，然后最后执行startProcessLocked。

{% highlight java linenos %} 
public final class ActivityManagerService extends ActivityManagerNative
		implements Watchdog.Monitor, BatteryStatsImpl.BatteryCallback {

	......

	private final void startProcessLocked(ProcessRecord app,
				String hostingType, String hostingNameStr) {

		......

		try {
			int uid = app.info.uid;
			int[] gids = null;
			try {
				gids = mContext.getPackageManager().getPackageGids(
					app.info.packageName);
			} catch (PackageManager.NameNotFoundException e) {
				......
			}
			
			......

			int debugFlags = 0;
			
			......
			
			// Start the process.  It will either succeed and return a result containing
            // the PID of the new process, or else throw a RuntimeException.
            Process.ProcessStartResult startResult = Process.start("android.app.ActivityThread",
                    app.processName, uid, uid, gids, debugFlags, mountExternal,
                    app.info.targetSdkVersion, null, null);			
			......

			if (app.persistent) {
                Watchdog.getInstance().processStarted(app.processName, startResult.pid);
            }

		} catch (RuntimeException e) {
			
			......

		}
	}

	......

}

{% endhighlight %}
这里主要是调用Process.start接口来创建一个新的进程，新的进程会导入android.app.ActivityThread类，并且执行它的main函数，这就是为什么我们前面说每一个应用程序都有一个ActivityThread实例来对应的原因。
查看ActivityThread.java的main方法。


{% highlight java linenos %} 
public final class ActivityThread {

	......

	private final void attach(boolean system) {
		......

		mSystemThread = system;
		if (!system) {

			......

			IActivityManager mgr = ActivityManagerNative.getDefault();
			try {
				mgr.attachApplication(mAppThread);
			} catch (RemoteException ex) {
			}
		} else {

			......

		}
	}

	......

	public static final void main(String[] args) {
		
		.......

		ActivityThread thread = new ActivityThread();
		thread.attach(false);

		......

		Looper.loop();

		.......

		thread.detach();
		
		......
	}
}
{% endhighlight %}
 这个函数在进程中创建一个ActivityThread实例，然后调用它的attach函数，接着就进入消息循环了，直到最后进程退出。
 函数attach最终调用了ActivityManagerService的远程接口ActivityManagerProxy的attachApplication函数，传入的参数是mAppThread，这是一个ApplicationThread类型的Binder对象，它的作用是用来进行进程间通信的。
查看代码 ActivityManagerService.attachApplication

{% highlight java linenos %} 
public final void attachApplication(IApplicationThread thread) {
        synchronized (this) {
            int callingPid = Binder.getCallingPid();
            final long origId = Binder.clearCallingIdentity();
            attachApplicationLocked(thread, callingPid);
            Binder.restoreCallingIdentity(origId);
        }
    }


private final boolean attachApplicationLocked(IApplicationThread thread,
            int pid) {

        // Find the application record that is being attached...  either via
        // the pid if we are running in multiple processes, or just pull the
        // next app record if we are emulating process with anonymous threads.
        ProcessRecord app;

		......

		if (pid != MY_PID && pid >= 0) {
			synchronized (mPidsSelfLocked) {
				app = mPidsSelfLocked.get(pid);
			}
		} else {
			app = null;
		}

		......

        String processName = app.processName;
        try {
            AppDeathRecipient adr = new AppDeathRecipient(
                    app, pid, thread);
            thread.asBinder().linkToDeath(adr, 0);
            app.deathRecipient = adr;
        } catch (RemoteException e) {
            app.resetPackageList();
            startProcessLocked(app, "link fail", processName);
            return false;
        }
        
        app.thread = thread;
        app.curAdj = app.setAdj = -100;
        app.curSchedGroup = Process.THREAD_GROUP_DEFAULT;
        app.setSchedGroup = Process.THREAD_GROUP_BG_NONINTERACTIVE;
        app.forcingToForeground = null;
        app.foregroundServices = false;
        app.hasShownUi = false;
        app.debugging = false;

        mHandler.removeMessages(PROC_START_TIMEOUT_MSG, app);

        boolean normalMode = mProcessesReady || isAllowedWhileBooting(app.info);
        List providers = normalMode ? generateApplicationProvidersLocked(app) : null;

        // Remove this record from the list of starting applications.
        mPersistentStartingProcesses.remove(app);

        mProcessesOnHold.remove(app);

        boolean badApp = false;
        boolean didSomething = false;

        // See if the top visible activity is waiting to run in this process...
        ActivityRecord hr = mMainStack.topRunningActivityLocked(null);
        if (hr != null && normalMode) {
            if (hr.app == null && app.uid == hr.info.applicationInfo.uid
                    && processName.equals(hr.processName)) {
                try {
                    if (mHeadless) {
                        Slog.e(TAG, "Starting activities not supported on headless device: " + hr);
                    } else if (mMainStack.realStartActivityLocked(hr, app, true, true)) {
                        didSomething = true;
                    }
                } catch (Exception e) {
                    badApp = true;
                }
            } else {
                mMainStack.ensureActivitiesVisibleLocked(hr, null, processName, 0);
            }
        }

        // Find any services that should be running in this process...
        if (!badApp) {
            try {
                didSomething |= mServices.attachApplicationLocked(app, processName);
            } catch (Exception e) {
                badApp = true;
            }
        }

        // Check if a next-broadcast receiver is in this process...
        if (!badApp && isPendingBroadcastProcessLocked(pid)) {
            try {
                didSomething = sendPendingBroadcastsLocked(app);
            } catch (Exception e) {
                // If the app died trying to launch the receiver we declare it 'bad'
                badApp = true;
            }
        }
		......

        return true;
    }


{% endhighlight %}
  已经创建了一个ProcessRecord，这里首先通过pid将它取回来，放在app变量中，然后对app的其它成员进行初始化，最后调用mMainStack.realStartActivityLocked执行真正的Activity启动操作。这里要启动的Activity通过调用mMainStack.topRunningActivityLocked(null)从堆栈顶端取回来，这时候在堆栈顶端的Activity就是MainActivity了。
查看ActivityStack.java的realStartActivityLocked


{% highlight java linenos %} 
public class ActivityStack {

	......

	final boolean realStartActivityLocked(ActivityRecord r,
			ProcessRecord app, boolean andResume, boolean checkConfig)
			throws RemoteException {
		
		......

		r.app = app;

		......

		int idx = app.activities.indexOf(r);
		if (idx < 0) {
			app.activities.add(r);
		}
		
		......

		try {
			......

			List<ResultInfo> results = null;
			List<Intent> newIntents = null;
			if (andResume) {
				results = r.results;
				newIntents = r.newIntents;
			}
	
			......
			
			app.thread.scheduleLaunchActivity(new Intent(r.intent), r,
				System.identityHashCode(r),
				r.info, r.icicle, results, newIntents, !andResume,
				mService.isNextTransitionForward());

			......

		} catch (RemoteException e) {
			......
		}

		......

		return true;
	}

	......

}
{% endhighlight %}

这里最终通过app.thread进入到ApplicationThreadProxy的scheduleLaunchActivity函数中，注意，这里的第二个参数r，是一个ActivityRecord类型的Binder对象，用来作来这个Activity的token值。调用的远端的ActivityThread.的scheduleLaunchActivity函数.
{% highlight java linenos %} 
        public final void scheduleLaunchActivity(Intent intent, IBinder token, int ident,
                ActivityInfo info, Configuration curConfig, CompatibilityInfo compatInfo,
                Bundle state, List<ResultInfo> pendingResults,
                List<Intent> pendingNewIntents, boolean notResumed, boolean isForward,
                String profileName, ParcelFileDescriptor profileFd, boolean autoStopProfiler) {
            ActivityClientRecord r = new ActivityClientRecord();

            r.token = token;
            r.ident = ident;
            r.intent = intent;
            r.activityInfo = info;
            r.compatInfo = compatInfo;
            r.state = state;

            r.pendingResults = pendingResults;
            r.pendingIntents = pendingNewIntents;

            r.startsNotResumed = notResumed;
            r.isForward = isForward;

            r.profileFile = profileName;
            r.profileFd = profileFd;
            r.autoStopProfiler = autoStopProfiler;

            updatePendingConfiguration(curConfig);

            queueOrSendMessage(H.LAUNCH_ACTIVITY, r);
        }

	private final class H extends Handler {

		......

		public void handleMessage(Message msg) {
			......
			switch (msg.what) {
			case LAUNCH_ACTIVITY: {
				ActivityClientRecord r = (ActivityClientRecord)msg.obj;

				r.packageInfo = getPackageInfoNoCheck(
					r.activityInfo.applicationInfo);
				handleLaunchActivity(r, null);
			} break;
			......
			}

		......

	}

	private void handleLaunchActivity(ActivityClientRecord r, Intent customIntent) {
        // If we are getting ready to gc after going to the background, well
        // we are back active so skip it.
        unscheduleGcIdler();

        ......
        Activity a = performLaunchActivity(r, customIntent);
		......
        if (a != null) {
            r.createdConfig = new Configuration(mConfiguration);
            Bundle oldState = r.state;
            handleResumeActivity(r.token, false, r.isForward,
                    !r.activity.mFinished && !r.startsNotResumed);
		......

    }
	......
}
{% endhighlight %}
1. 这里首先调用performLaunchActivity函数来加载这个Activity类，在performLaunchActivity中，如果没有application会先创建新的application，并调用application的onCreate方法。
2. 最后回到handleLaunchActivity函数时，再调用handleResumeActivity函数来使这个Activity进入Resumed状态，即会调用这个Activity的onResume函数，这是遵循Activity的生命周期的。
performLaunchActivity函数代码:
	{% highlight java linenos %} 
	private Activity performLaunchActivity(ActivityClientRecord r, Intent customIntent) {
        ActivityInfo aInfo = r.activityInfo;
        if (r.packageInfo == null) {
            r.packageInfo = getPackageInfo(aInfo.applicationInfo, r.compatInfo,
                    Context.CONTEXT_INCLUDE_CODE);
        }

        ComponentName component = r.intent.getComponent();
        if (component == null) {
            component = r.intent.resolveActivity(
                mInitialApplication.getPackageManager());
            r.intent.setComponent(component);
        }

        if (r.activityInfo.targetActivity != null) {
            component = new ComponentName(r.activityInfo.packageName,
                    r.activityInfo.targetActivity);
        }

        Activity activity = null;
        try {
            java.lang.ClassLoader cl = r.packageInfo.getClassLoader();
            activity = mInstrumentation.newActivity(
                    cl, component.getClassName(), r.intent);
            StrictMode.incrementExpectedActivityCount(activity.getClass());
            r.intent.setExtrasClassLoader(cl);
            if (r.state != null) {
                r.state.setClassLoader(cl);
            }
        } catch (Exception e) {

        }

        try {
            Application app = r.packageInfo.makeApplication(false, mInstrumentation);

            if (activity != null) {
                Context appContext = createBaseContextForActivity(r, activity);
                CharSequence title = r.activityInfo.loadLabel(appContext.getPackageManager());
                Configuration config = new Configuration(mCompatConfiguration);
                if (DEBUG_CONFIGURATION) Slog.v(TAG, "Launching activity "
                        + r.activityInfo.name + " with config " + config);
                activity.attach(appContext, this, getInstrumentation(), r.token,
                        r.ident, app, r.intent, r.activityInfo, title, r.parent,
                        r.embeddedID, r.lastNonConfigurationInstances, config);

                if (customIntent != null) {
                    activity.mIntent = customIntent;
                }
                r.lastNonConfigurationInstances = null;
                activity.mStartedActivity = false;
                int theme = r.activityInfo.getThemeResource();
                if (theme != 0) {
                    activity.setTheme(theme);
                }

                activity.mCalled = false;
                mInstrumentation.callActivityOnCreate(activity, r.state);
                if (!activity.mCalled) {
                    throw new SuperNotCalledException(
                        "Activity " + r.intent.getComponent().toShortString() +
                        " did not call through to super.onCreate()");
                }
                r.activity = activity;
                r.stopped = true;
                if (!r.activity.mFinished) {
                    activity.performStart();
                    r.stopped = false;
                }
                if (!r.activity.mFinished) {
                    if (r.state != null) {
                        mInstrumentation.callActivityOnRestoreInstanceState(activity, r.state);
                    }
                }
                if (!r.activity.mFinished) {
                    activity.mCalled = false;
                    mInstrumentation.callActivityOnPostCreate(activity, r.state);
                    if (!activity.mCalled) {
                        throw new SuperNotCalledException(
                            "Activity " + r.intent.getComponent().toShortString() +
                            " did not call through to super.onPostCreate()");
                    }
                }
            }
            r.paused = true;

            mActivities.put(r.token, r);

        } catch (SuperNotCalledException e) {
            throw e;

        } catch (Exception e) {
            if (!mInstrumentation.onException(activity, e)) {
                throw new RuntimeException(
                    "Unable to start activity " + component
                    + ": " + e.toString(), e);
            }
        }

        return activity;
    }
	{% endhighlight %}
函数前面是收集要启动的Activity的相关信息，主要package和component信息	

{% highlight java linenos %} 
   ActivityInfo aInfo = r.activityInfo;
   if (r.packageInfo == null) {
        r.packageInfo = getPackageInfo(aInfo.applicationInfo,
                Context.CONTEXT_INCLUDE_CODE);
   }

   ComponentName component = r.intent.getComponent();
   if (component == null) {
       component = r.intent.resolveActivity(
           mInitialApplication.getPackageManager());
       r.intent.setComponent(component);
   }

   if (r.activityInfo.targetActivity != null) {
       component = new ComponentName(r.activityInfo.packageName,
               r.activityInfo.targetActivity);
   }

{% endhighlight %}
 然后通过ClassLoader将目标的Activity的new出来

{% highlight java linenos %} 
   Activity activity = null;
   try {
	java.lang.ClassLoader cl = r.packageInfo.getClassLoader();
	activity = mInstrumentation.newActivity(
		cl, component.getClassName(), r.intent);
	r.intent.setExtrasClassLoader(cl);
	if (r.state != null) {
		r.state.setClassLoader(cl);
	}
   } catch (Exception e) {
	......
   }

{% endhighlight %}
接下来是创建Application对象，这是根据AndroidManifest.xml配置文件中的Application标签的信息来创建的：
{% highlight java linenos %} 
Application app = r.packageInfo.makeApplication(false, mInstrumentation);
{% endhighlight %}
后面的代码主要创建Activity的上下文信息，并通过attach方法将这些上下文信息设置到MainActivity中去：
{% highlight java linenos %} 
				Context appContext = createBaseContextForActivity(r, activity);
                CharSequence title = r.activityInfo.loadLabel(appContext.getPackageManager());
                Configuration config = new Configuration(mCompatConfiguration);
                activity.attach(appContext, this, getInstrumentation(), r.token,
                        r.ident, app, r.intent, r.activityInfo, title, r.parent,
                        r.embeddedID, r.lastNonConfigurationInstances, config);

                if (customIntent != null) {
                    activity.mIntent = customIntent;
                }
                r.lastNonConfigurationInstances = null;
                activity.mStartedActivity = false;
                int theme = r.activityInfo.getThemeResource();
                if (theme != 0) {
                    activity.setTheme(theme);
                }
{% endhighlight %}
最后还要调用MainActivity的onCreate函数：
{% highlight java linenos %} 
mInstrumentation.callActivityOnCreate(activity, r.state);
{% endhighlight %}




### 结论

1.androd的底层实现是通过socket和共享内存的方式，这种写法也可以采用在我们自己的多进程通信上使用，值得学习
2.底层所有的event其实都是一样的，都是inputEvent，上层会根据source再分成keyEvent,MotionEvent等，用于不同的用处 
3.所有View的起点其实就是dispatchPointerEvent()，这个是分发事件的起点.


### 参考blog
[本文基于android-2.3.3_r1代码研究]: http://daemon369.github.io/android/2014/09/11/android-dispatchTouchEvent/  "本文基于android-2.3.3_r1代码研究"
[Android事件分发机制完全解析，带你从源码的角度彻底理解]: http://blog.csdn.net/guolin_blog/article/details/9153747 "Android事件分发机制完全解析，带你从源码的角度彻底理解"
[android-inputevent传递过程]:http://blog.pickbox.me/2014/05/22/android-inputevent传递过程（app端）/ "android-inputevent传递过程"


[yangming]:  
