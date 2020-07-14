package {{ args.package }};

import android.content.Context;
import android.content.Intent;
import org.kivy.android.PythonService;

public class Service{{ name|capitalize }} extends PythonService {

    {% if sticky %}
    @Override
    public int startType() {
        return START_STICKY;
    }

    {% endif %}
    @Override
    protected int getServiceId() {
        return {{ service_id }};
    }

    public static void start(Context ctx, String pythonServiceArgument) {
        String argument = ctx.getFilesDir().getAbsolutePath() + "/app";
        Intent intent = new Intent(ctx, Service{{ name|capitalize }}.class);
        intent.putExtra("androidArgument", argument);
        intent.putExtra("androidPrivate", ctx.getFilesDir().getAbsolutePath());

        intent.putExtra("serviceDescription", "{{ name|capitalize }}");
        intent.putExtra("serviceEntrypoint", "{{ entrypoint }}");
        intent.putExtra("serviceTitle", "{{ args.name }}");
        intent.putExtra("pythonName", "{{ name }}");
        intent.putExtra("serviceStartAsForeground", "{{ foreground|lower }}");
        intent.putExtra("pythonHome", argument);
        intent.putExtra("pythonPath", argument + ":" + argument + "/lib");
        intent.putExtra("pythonServiceArgument", pythonServiceArgument);
        ctx.startService(intent);
    }

    public static void stop(Context ctx) {
        Intent intent = new Intent(ctx, Service{{ name|capitalize }}.class);
        ctx.stopService(intent);
    }

}
