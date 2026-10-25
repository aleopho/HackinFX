// SPDX-License-Identifier: GPL-2.0-or-later
import Foundation
@main struct VersionTests {
 static func main() {
  precondition(ReleaseVersion.isNewer("v2.10.0",than:"2.9.9"))
  precondition(!ReleaseVersion.isNewer("2.0",than:"2.0.0"))
  precondition(!ReleaseVersion.isNewer("1.1.1",than:"2.0.3"))
  for bad in ["v2.0.4-beta","2..4","-2.0.4","٢.٠.٤","2.0.4.1",""] { precondition(ReleaseVersion.components(bad)==nil) }
  print("Stable release comparison and invalid version rejection verified")
 }
}
