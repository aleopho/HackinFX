// SPDX-License-Identifier: GPL-3.0-or-later
package community.aleopho.hackinfx;
import android.app.Application;
import java.io.*;
import java.nio.charset.StandardCharsets;
/** Private crash trace without exception messages, tokens or pairing data. */
public final class RemoteApplication extends Application {
    @Override public void onCreate(){super.onCreate();Thread.UncaughtExceptionHandler previous=Thread.getDefaultUncaughtExceptionHandler();Thread.setDefaultUncaughtExceptionHandler((thread,error)->{try(FileOutputStream out=openFileOutput("last-crash.txt",MODE_PRIVATE)){StringBuilder s=new StringBuilder("HackinFX Remote 1.2.0\nAndroid API "+android.os.Build.VERSION.SDK_INT+"\n");Throwable e=error;for(int cause=0;e!=null&&cause<4;cause++,e=e.getCause()){s.append(e.getClass().getName()).append('\n');StackTraceElement[] frames=e.getStackTrace();for(int i=0;i<Math.min(24,frames.length);i++)s.append("  ").append(frames[i]).append('\n');}out.write(s.toString().getBytes(StandardCharsets.UTF_8));}catch(Exception ignored){}if(previous!=null)previous.uncaughtException(thread,error);else android.os.Process.killProcess(android.os.Process.myPid());});}
}
