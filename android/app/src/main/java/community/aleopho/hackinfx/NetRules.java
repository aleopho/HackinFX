// SPDX-License-Identifier: GPL-3.0-or-later
package community.aleopho.hackinfx;
public final class NetRules {
    private NetRules() {}
    public static boolean localHost(String host) {
        if(host==null || !host.matches("[0-9]{1,3}(\\.[0-9]{1,3}){3}")) return false;
        String[] s=host.split("\\.");int[] n=new int[4];
        for(int i=0;i<4;i++){if(s[i].length()>1 && s[i].startsWith("0"))return false;n[i]=Integer.parseInt(s[i]);if(n[i]>255)return false;}
        return n[0]==10 || n[0]==172 && n[1]>=16 && n[1]<=31 || n[0]==192 && n[1]==168;
    }
    public static boolean pin(String value){return value!=null && value.matches("[a-fA-F0-9]{64}");}
    public static boolean color(String value){return value!=null && value.matches("[a-fA-F0-9]{6}");}
}
