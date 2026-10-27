// SPDX-License-Identifier: GPL-2.0-or-later
import Foundation
struct WidgetSnapshot:Decodable {
    let schema:Int
    let appName:String
    let effect:String
    let activeDevices:Int
    let running:Bool
    let colors:[String]
    let brightness:Double
    let updatedAt:Date
    static let empty=Self(schema:2,appName:"HackinFX",effect:"Offline",activeDevices:0,running:false,colors:["9bed4b"],brightness:0,updatedAt:.distantPast)
    static func decode(_ data:Data)->Self? {
        guard data.count<=8192 else { return nil }
        let decoder=JSONDecoder();decoder.dateDecodingStrategy = .iso8601
        guard let value=try? decoder.decode(Self.self,from:data),value.schema==2,value.appName=="HackinFX",value.effect.count<=80,(0...192).contains(value.activeDevices),value.brightness.isFinite,(0...100).contains(value.brightness),value.colors.count<=8,value.colors.allSatisfy({$0.count==6 && UInt32($0,radix:16) != nil}) else { return nil }
        return value
    }
    static func fetch(port:Int=49731,completion:@escaping(Self)->Void) {
        guard port<=49734 else { completion(.empty);return }
        let configuration=URLSessionConfiguration.ephemeral;configuration.timeoutIntervalForRequest=1.5;configuration.timeoutIntervalForResource=2
        let session=URLSession(configuration:configuration)
        session.dataTask(with:URL(string:"http://localhost:\(port)/v1/widget")!) { data,response,_ in
            defer { session.finishTasksAndInvalidate() }
            if let data=data,(response as? HTTPURLResponse)?.statusCode==200,let value=decode(data) { completion(value) }
            else { fetch(port:port+1,completion:completion) }
        }.resume()
    }
}
